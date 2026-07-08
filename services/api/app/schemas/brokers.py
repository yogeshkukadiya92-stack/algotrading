from pydantic import BaseModel, Field


class BrokerCredentialCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    broker_account_id: str = Field(min_length=1, max_length=80)
    broker_name: str = Field(min_length=1, max_length=80)
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)


class BrokerCredentialResponse(BaseModel):
    id: str
    user_id: str
    broker_account_id: str
    broker_name: str
    is_active: bool

