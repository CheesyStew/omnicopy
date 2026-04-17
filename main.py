from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from datetime import datetime , date , timezone
from typing import Annotated, Generic, TypeVar
from sqlmodel import create_engine
from sqlmodel import Field, Session, SQLModel, create_engine, select
from pydantic import BaseModel

class Campaign(SQLModel, table=True):
    campaign_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    due_date: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory= lambda : datetime.now(timezone.utc), index=True)

class CampaignCreate(SQLModel):
    name: str
    due_date: datetime | None = None

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)  

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        if not session.exec(select(Campaign)).first():
            session.add_all([
                Campaign(name="Summer Launch", due_date=datetime.now(timezone.utc)),
                Campaign(name="Black Friday", due_date=datetime.now(timezone.utc))
            ])
            session.commit()
    yield

app = FastAPI(root_path="/api/v1" , lifespan=lifespan)

# data : Any = [
#         {
#             "campaign_id": 1, 
#             "name": "Summer Launch", 
#             "due_date": datetime.now(),
#             "created_at": datetime.now()
#          }, 
#          {
#              "campaign_id": 2, 
#              "name": "Black Friday", 
#              "due_date": datetime.now(), 
#              "created_at": datetime.now()}]

@app.get("/")
async def root():
    return {"message": "Hello World"}

'''
Campaigns
- campaign_id
- name
- due_date
- created_at

pieces
- piece_id
- campaign_id
- name
- content
- content_type
- created_at
'''

T = TypeVar("T")
class Response(BaseModel, Generic[T]):
    data: T


@app.get("/campaigns", response_model=Response[list[Campaign]])
async def read_campaigns(session: SessionDep):
    data = session.exec(select(Campaign)).all()
    return {"data": data}

@app.get("/campaigns/{id}", response_model=Response[Campaign])
async def read_campaign(id: int, session: SessionDep):
    data = session.get(Campaign, id)
    if not data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"data": data}

@app.post("/campaigns" , status_code=201, response_model=Response[Campaign])
async def create_campaign(campaign: CampaignCreate, session: SessionDep):
    db_campaign = Campaign.model_validate(campaign)
    session.add(db_campaign)
    session.commit()
    session.refresh(db_campaign)
    return {"data": db_campaign}

@app.put("/campaigns/{id}", status_code=200, response_model=Response[Campaign])
async def update_campaign(id: int, campaign: CampaignCreate, session: SessionDep):
    db_campaign = Campaign.model_validate(campaign)
    data = session.get(Campaign, id)
    if not data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    data.name = db_campaign.name
    data.due_date = db_campaign.due_date
    session.add(data)
    session.commit()
    session.refresh(data)
    return {"data": data}

@app.delete("/campaigns/{id}", status_code=204)
async def delete_campaign(id: int, session: SessionDep):
    data = session.get(Campaign, id)
    if not data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    session.delete(data)
    session.commit()
    
    

# @app.delete("/campaigns/{id}")
# async def delete_campaign(id: int):
#     for index , campaign in enumerate(data):
#         if campaign.get("campaign_id") == id:
#             data.pop(index)
#             return{"message": "Campaign deleted successfully", "response": Response(status_code=204)}
#     raise HTTPException(status_code=404, detail="Campaign not found")