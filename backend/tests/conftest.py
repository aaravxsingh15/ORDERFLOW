import pandas as pd
import pytest

import synthetic_data
from ml import feature_config as fc


@pytest.fixture(scope="session")
def raw_orders() -> pd.DataFrame:
    return synthetic_data.generate_orders(400, seed=5)


@pytest.fixture()
def one_order() -> dict:
    return dict(order_id="ZF2048", order_time="20:15", day_of_week="Friday", num_items=5, order_value=840, prep_time=24,
                restaurant_load="High", rider_assignment_delay=8, pickup_wait=6, distance_km=7.2, traffic_level="Heavy",
                weather="Rain", area_type="Dense Urban", rider_experience="Moderate", peak_hour=True, batch_delivery=False,
                promised_eta=None)


@pytest.fixture(scope="session")
def service():
    from model_service import service as svc
    svc.load()
    return svc


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c


def as_text(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype(str)


GRACE = fc.DELAY_GRACE_MINUTES
