from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.sanitization import mask_sensitive_data
from app.models import AuditEvent, BrokerAccount, User
from app.schemas.brokers import BrokerConnectRequest
from app.services.broker_resilience import CircuitBreakerOpenError, broker_circuit_breaker

CURRENT_FILE = Path(__file__).resolve()
ROOT_CANDIDATES = [Path.cwd(), *CURRENT_FILE.parents, Path("/")]
for root_candidate in ROOT_CANDIDATES:
    for package_path in (
        root_candidate / "packages" / "broker_core",
        root_candidate / "packages" / "broker_upstox",
        root_candidate / "packages" / "broker_zerodha",
    ):
        if package_path.exists() and str(package_path) not in sys.path:
            sys.path.insert(0, str(package_path))

from broker_core import BrokerNetworkError, BrokerNotImplementedError
from broker_upstox import UpstoxReadOnlyAdapter
from broker_zerodha import ZerodhaReadOnlyAdapter


class UrlLibBrokerHttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        req = request.Request(f"{self.base_url}{path}", headers=headers or {}, method="GET")
        return self._load(req)

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        encoded = json.dumps(data or {}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=encoded,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        return self._load(req)

    def _load(self, req: request.Request) -> dict:
        try:
            with request.urlopen(req, timeout=get_settings().broker_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise BrokerNetworkError("Broker request timed out") from exc
        except urllib_error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError | socket.timeout):
                raise BrokerNetworkError("Broker request timed out") from exc
            raise BrokerNetworkError("Broker request failed") from exc


class AuditedBrokerHttpClient:
    def __init__(
        self,
        *,
        inner,
        service: BrokerReadOnlyService,
        db: Session,
        user: User,
        account: BrokerAccount,
    ) -> None:
        self.inner = inner
        self.service = service
        self.db = db
        self.user = user
        self.account = account

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        self.service.audit(
            self.db,
            user_id=self.user.id,
            event_type="broker.http.request",
            broker_account_id=self.account.id,
            message=f"Broker HTTP request {path}",
            payload={"broker_name": self.account.broker_name, "method": "GET", "path": path, "headers": headers or {}},
        )
        response = self.inner.get(path, headers=headers)
        self.service.audit(
            self.db,
            user_id=self.user.id,
            event_type="broker.http.response",
            broker_account_id=self.account.id,
            message=f"Broker HTTP response {path}",
            payload={"broker_name": self.account.broker_name, "method": "GET", "path": path, "response": response},
        )
        return response

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        self.service.audit(
            self.db,
            user_id=self.user.id,
            event_type="broker.http.request",
            broker_account_id=self.account.id,
            message=f"Broker HTTP request {path}",
            payload={"broker_name": self.account.broker_name, "method": "POST", "path": path, "body": data or {}, "headers": headers or {}},
        )
        response = self.inner.post(path, data=data, headers=headers)
        self.service.audit(
            self.db,
            user_id=self.user.id,
            event_type="broker.http.response",
            broker_account_id=self.account.id,
            message=f"Broker HTTP response {path}",
            payload={"broker_name": self.account.broker_name, "method": "POST", "path": path, "response": response},
        )
        return response


class BrokerReadOnlyService:
    def __init__(self) -> None:
        self.http_client_factory = lambda base_url: UrlLibBrokerHttpClient(base_url)
        self._broker_configs = {
            "zerodha": {
                "default_display_name": "Zerodha Read Only",
                "api_key_env": "ZERODHA_API_KEY",
                "access_token_env": "ZERODHA_ACCESS_TOKEN",
                "redirect_uri_env": "ZERODHA_REDIRECT_URI",
                "base_url_env": "ZERODHA_API_BASE_URL",
                "default_base_url": "https://api.kite.trade",
            },
            "upstox": {
                "default_display_name": "Upstox Read Only",
                "api_key_env": "UPSTOX_API_KEY",
                "access_token_env": "UPSTOX_ACCESS_TOKEN",
                "redirect_uri_env": "UPSTOX_REDIRECT_URI",
                "base_url_env": "UPSTOX_API_BASE_URL",
                "default_base_url": "https://api.upstox.com",
            },
        }

    def list_accounts(self, db: Session, user: User) -> list[BrokerAccount]:
        return list(
            db.scalars(
                select(BrokerAccount)
                .where(BrokerAccount.user_id == user.id)
                .order_by(BrokerAccount.created_at.desc())
            ).all()
        )

    def connect(self, db: Session, user: User, payload: BrokerConnectRequest) -> tuple[BrokerAccount, str]:
        broker_name = payload.broker_name.value
        adapter = self._build_adapter_by_name(broker_name, access_token=None)
        login_url = adapter.login_url()
        config = self._require_broker_config(broker_name)
        account = BrokerAccount(
            user_id=user.id,
            broker_name=broker_name,
            display_name=payload.display_name.strip() or config["default_display_name"],
            encrypted_api_key=self._placeholder_secret(config["api_key_env"]),
            encrypted_access_token=self._placeholder_secret(config["access_token_env"]),
            is_active=True,
            is_paper=False,
            static_ip_verified=False,
        )
        db.add(account)
        db.flush()
        self.audit(
            db,
            user_id=user.id,
            event_type="broker.connect",
            broker_account_id=account.id,
            message="Read-only broker account connected",
            payload={"broker_name": broker_name, "request_token_present": bool(payload.request_token)},
        )
        db.commit()
        db.refresh(account)
        return account, login_url

    def get_account(self, db: Session, user: User, broker_account_id: str) -> BrokerAccount:
        account = db.get(BrokerAccount, broker_account_id)
        if account is None or account.user_id != user.id:
            raise LookupError("Broker account not found")
        return account

    def get_profile(self, db: Session, user: User, account: BrokerAccount):
        return self._audited_call(db, user, account, "broker.profile", "/user/profile", lambda adapter: adapter.get_profile())

    def get_funds(self, db: Session, user: User, account: BrokerAccount):
        return self._audited_call(db, user, account, "broker.funds", "/user/margins", lambda adapter: adapter.get_funds())

    def get_positions(self, db: Session, user: User, account: BrokerAccount):
        return self._audited_call(
            db, user, account, "broker.positions", "/portfolio/positions", lambda adapter: adapter.get_positions()
        )

    def get_orders(self, db: Session, user: User, account: BrokerAccount):
        return self._audited_call(db, user, account, "broker.orders", "/orders", lambda adapter: adapter.get_orders())

    def place_order(self, db: Session, user: User, account: BrokerAccount, order):
        return self._audited_call(db, user, account, "broker.place_order", "/orders/regular", lambda adapter: adapter.place_order(order))

    def disabled_order_error(self) -> BrokerNotImplementedError:
        return BrokerNotImplementedError("Live broker order placement is disabled in this phase")

    def audit(
        self,
        db: Session,
        *,
        user_id: str | None,
        event_type: str,
        broker_account_id: str | None,
        message: str,
        payload: dict[str, Any],
    ) -> None:
        db.add(
            AuditEvent(
                user_id=user_id,
                event_type=event_type,
                entity_type="broker_account",
                entity_id=broker_account_id,
                message=message,
                raw_payload=self._redact(payload),
            )
        )

    def _audited_call(self, db: Session, user: User, account: BrokerAccount, event: str, path: str, call):
        breaker_key = f"{account.broker_name}:{path}"
        self.audit(
            db,
            user_id=user.id,
            event_type=f"{event}.request",
            broker_account_id=account.id,
            message=f"Broker API request {path}",
            payload={
                "broker_name": account.broker_name,
                "path": path,
                "method": "GET",
                "circuit_breaker": broker_circuit_breaker.snapshot(breaker_key),
            },
        )
        adapter = self._adapter_for_account(db, user, account)
        try:
            result = broker_circuit_breaker.protect(breaker_key, lambda: call(adapter))
        except CircuitBreakerOpenError as exc:
            self.audit(
                db,
                user_id=user.id,
                event_type=f"{event}.blocked",
                broker_account_id=account.id,
                message=f"Broker API request blocked by circuit breaker for {path}",
                payload={"broker_name": account.broker_name, "path": path, "error": str(exc)},
            )
            db.commit()
            raise BrokerNetworkError(str(exc)) from exc
        except Exception as exc:
            self.audit(
                db,
                user_id=user.id,
                event_type=f"{event}.error",
                broker_account_id=account.id,
                message=f"Broker API request failed for {path}",
                payload={"broker_name": account.broker_name, "path": path, "error": str(exc)},
            )
            db.commit()
            raise
        self.audit(
            db,
            user_id=user.id,
            event_type=f"{event}.response",
            broker_account_id=account.id,
            message=f"Broker API response {path}",
            payload={"broker_name": account.broker_name, "path": path, "response": self._to_payload(result)},
        )
        db.commit()
        return result

    def _adapter_for_account(self, db: Session, user: User, account: BrokerAccount):
        config = self._require_broker_config(account.broker_name)
        base_client = self.http_client_factory(os.getenv(config["base_url_env"], config["default_base_url"]))
        audited_client = AuditedBrokerHttpClient(
            inner=base_client,
            service=self,
            db=db,
            user=user,
            account=account,
        )
        return self._build_adapter_by_name(
            account.broker_name,
            access_token=os.getenv(config["access_token_env"]),
            http_client=audited_client,
        )

    def _build_adapter_by_name(self, broker_name: str, access_token: str | None, http_client=None):
        config = self._require_broker_config(broker_name)
        client = http_client or self.http_client_factory(os.getenv(config["base_url_env"], config["default_base_url"]))
        if broker_name == "zerodha":
            return ZerodhaReadOnlyAdapter(
                api_key=os.getenv(config["api_key_env"], "missing_zerodha_api_key"),
                access_token=access_token,
                redirect_uri=os.getenv(config["redirect_uri_env"]),
                http_client=client,
            )
        if broker_name == "upstox":
            return UpstoxReadOnlyAdapter(
                api_key=os.getenv(config["api_key_env"], "missing_upstox_api_key"),
                access_token=access_token,
                redirect_uri=os.getenv(config["redirect_uri_env"]),
                http_client=client,
            )
        raise ValueError("Unsupported broker")

    def _require_broker_config(self, broker_name: str) -> dict[str, str]:
        config = self._broker_configs.get(broker_name)
        if config is None:
            raise ValueError("Unsupported broker")
        return config

    def _placeholder_secret(self, name: str) -> str:
        return f"encrypted_env_placeholder:{name}"

    def _to_payload(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._to_payload(item) for item in value]
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value

    def _redact(self, payload: dict[str, Any]) -> dict[str, Any]:
        return mask_sensitive_data(payload)


broker_readonly_service = BrokerReadOnlyService()
