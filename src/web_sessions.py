"""Explicit localhost demo role sessions. Not production authentication or SSO."""
import secrets
import time
from threading import Lock
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

COOKIE='policy_demo_session'
TTL=8*60*60
PROFILES={
    'employee':dict(employee_id='DEMO-001',role='employee',display_name='演示员工'),
    'finance':dict(employee_id='FINANCE-DEMO',role='finance',display_name='演示财务'),
}


class DemoLogin(BaseModel):
    model_config=ConfigDict(extra='forbid')
    profile: Literal['employee','finance']


class DemoSessions:
    def __init__(self):
        self.values={};self.lock=Lock()

    def create(self,profile,previous=None):
        with self.lock:
            stamp=time.monotonic()
            self.values={k:v for k,v in self.values.items() if v[0]>stamp}
            self.values.pop(previous,None)
            if len(self.values)>=256:raise HTTPException(429,'Demo session limit reached')
            token=secrets.token_urlsafe(48)
            self.values[token]=(stamp+TTL,PROFILES[profile].copy())
            return token

    def get(self,token):
        with self.lock:
            record=self.values.get(token)
            if not record:return None
            if record[0]<=time.monotonic():
                self.values.pop(token,None);return None
            return record[1].copy()

    def remove(self,token):
        with self.lock:self.values.pop(token,None)
