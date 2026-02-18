"""Shared data models for uvicoord."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PortStrategy(str, Enum):
    """Port allocation strategies."""
    DEDICATED = "dedicated"
    RANGE = "range"
    LIST = "list"
    STEPPED = "stepped"
    ANY = "any"


class SteppedPortConfig(BaseModel):
    """Configuration for stepped port allocation."""
    start: int = Field(..., ge=1024, le=65535)
    step: int = Field(default=1, ge=1)
    count: int = Field(default=10, ge=1)


class AppConfig(BaseModel):
    """Configuration for a registered application."""
    name: str
    path: str
    command: str = "uvicorn app.main:app --reload"
    port_strategy: PortStrategy = PortStrategy.ANY
    # For dedicated strategy
    port: Optional[int] = Field(default=None, ge=1024, le=65535)
    # For range strategy
    port_range: Optional[tuple[int, int]] = None
    # For list strategy
    ports: Optional[list[int]] = None
    # For stepped strategy
    port_step: Optional[SteppedPortConfig] = None
    
    def get_available_ports(self) -> list[int]:
        """Get list of all ports this app can use based on strategy."""
        match self.port_strategy:
            case PortStrategy.DEDICATED:
                return [self.port] if self.port else []
            case PortStrategy.RANGE:
                if self.port_range:
                    return list(range(self.port_range[0], self.port_range[1] + 1))
                return []
            case PortStrategy.LIST:
                return self.ports or []
            case PortStrategy.STEPPED:
                if self.port_step:
                    return [
                        self.port_step.start + (i * self.port_step.step)
                        for i in range(self.port_step.count)
                    ]
                return []
            case PortStrategy.ANY:
                return []  # Will use default range
        return []


class ActiveInstance(BaseModel):
    """Represents a running app instance."""
    app_name: str
    instance_id: str
    port: int
    pid: int
    started_at: str


class CoordinatorConfig(BaseModel):
    """Main configuration for the coordinator."""
    coordinator_port: int = 9000
    default_port_range: tuple[int, int] = (8100, 8199)
    apps: dict[str, AppConfig] = Field(default_factory=dict)


class PortRequest(BaseModel):
    """Request for a port allocation."""
    app_name: str
    instance_id: Optional[str] = None
    pid: int


class PortResponse(BaseModel):
    """Response with allocated port."""
    port: int
    app_name: str
    instance_id: str


class ReleaseRequest(BaseModel):
    """Request to release a port."""
    app_name: str
    instance_id: Optional[str] = None
    pid: Optional[int] = None
