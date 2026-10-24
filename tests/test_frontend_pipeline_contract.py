"""Test the real payload shape produced by frontend/assets/js/api.js."""
import importlib
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app

upload_module = importlib.import_module('backend.routers.upload')
clean_module = importlib.import_module('backend.routers.clean')
download_module = importlib.import_module('backend.routers.download')
profile_module = importlib.import_module('backend.routers.profile')


@pytest.fixture
def client_and_dirs(tmp_path, monkeypatch):
    raw = tmp_path / 'raw'
    processed = tmp_path / 'processed'
    raw.mkdir()
    processed.mkdir()
    for module in (upload_module, clean_module, profile_module):
        monkeypatch.setattr(module, 'RAW_DIR', raw)
    for module in (clean_module, download_module):
        monkeypatch.setattr(module, 'PROCESSED_DIR', processed)
    return TestClient(app), processed


def upload(client, content):
    response = client.post('/api/upload', files={'file': ('demo.csv', content, 'text/csv')})
    assert response.status_code == 200, response.text
    return response.json()['file_id']


def test_frontend_mean_produces_mean_not_default_median(client_and_dirs):
    client, processed = client_and_dirs
    file_id = upload(client, b'Name,Age\nAn,20\nBinh,21\nChi,40\nDung,\n')
    result = client.post('/api/clean', json={
        'file_id': file_id,
        'pipeline': [{'step_type': 'missing_values', 'config': {'columns': ['Age'], 'strategy': 'mean'}}],
    })
    assert result.status_code == 200, result.text
    audit = result.json()['audit_summary']
    assert (audit['initial_rows'], audit['final_rows']) == (4, 4)
    assert (audit['initial_columns'], audit['final_columns']) == (2, 2)
    assert audit['total_steps'] == 1
    assert audit['history'][0]['action'] == 'missing_values'
    assert pd.read_csv(processed / f'{file_id}.csv').loc[3, 'Age'] == 27


def test_multi_step_encoding_audit_and_download(client_and_dirs):
    client, processed = client_and_dirs
    fid = upload(client, b'City,Age\nHanoi,20\nHCM,\nHanoi,22\n')
    r = client.post('/api/clean', json={'file_id':fid,'pipeline':[
        {'step_type':'missing_values','config':{'columns':None,'strategy':'median'}},
        {'step_type':'encoding','config':{'columns':['City'],'method':'one_hot'}},
        {'step_type':'scaling','config':{'columns':['Age'],'method':'standard'}}
    ]})
    assert r.status_code == 200, r.text
    audit = r.json()['audit_summary']
    assert audit['total_steps'] == 3
    assert audit['initial_columns'] == 2
    assert audit['final_columns'] == 2  # City -> one dummy since drop_first=True
    assert len(audit['history']) == 3
    df = pd.read_csv(processed/f'{fid}.csv')
    assert abs(df['Age'].mean()) < 1e-9
    assert any(c.startswith('City_') for c in df.columns)
    dl = client.get(f'/api/download/{fid}?file_format=json')
    assert dl.status_code == 200
    assert len(dl.json()) == 3


def test_selected_currency_and_profile(client_and_dirs):
    client, processed = client_and_dirs
    fid = upload(client, 'Name,Salary\nAn,"$1,200.50"\nBinh,"1,500 đ"\nChi,2300\n'.encode())
    profile = client.get(f'/api/profile/{fid}')
    assert profile.status_code == 200
    assert profile.json()['total_rows'] == 3
    r = client.post('/api/clean', json={'file_id':fid,'pipeline':[
        {'step_type':'clean_numeric','config':{'columns':['Salary']}}
    ]})
    assert r.status_code == 200, r.text
    assert r.json()['audit_summary']['total_steps'] == 1
    df = pd.read_csv(processed/f'{fid}.csv')
    assert df['Name'].tolist() == ['An','Binh','Chi']
    assert df['Salary'].tolist() == [1200.5,1500.0,2300.0]


def test_reject_invalid_pipeline_without_corrupting_data(client_and_dirs):
    client, processed = client_and_dirs
    fid = upload(client,b'Name,Age\nAn,20\nBinh,21\n')
    r = client.post('/api/clean', json={'file_id':fid,'pipeline':[
        {'step_type':'clean_numeric','config':{'columns':['Name']}}
    ]})
    assert r.status_code == 400, r.text
    assert not (processed/f'{fid}.csv').exists()
    r = client.post('/api/clean', json={'file_id':fid,'pipeline':[
        {'step_type':'something_invalid','config':{}}
    ]})
    assert r.status_code == 422, r.text


def test_interpolation_legacy_alias(client_and_dirs):
    client, processed = client_and_dirs
    fid=upload(client,b'Age\n20\n\n24\n')
    # Pandas skips empty lines by default; include an explicit missing value.
    raw=clean_module.RAW_DIR / f'{fid}.csv'
    raw.write_text('Age\n20\nNA\n24\n',encoding='utf-8')
    r=client.post('/api/clean',json={'file_id':fid,'missing_method':'interpolate'})
    assert r.status_code == 200,r.text
    assert pd.read_csv(processed/f'{fid}.csv')['Age'].tolist()==[20,22,24]


def test_numeric_currency_negative_preserves_sign_and_rejects_text(client_and_dirs):
    client, processed = client_and_dirs
    fid = upload(client, 'Name,Money\nAn,"-$1,200.50"\nBinh,"+200 đ"\n'.encode())
    r = client.post('/api/clean', json={'file_id':fid,'pipeline':[
        {'step_type':'clean_numeric','config':{'columns':['Money']}}
    ]})
    assert r.status_code == 200, r.text
    df = pd.read_csv(processed/f'{fid}.csv')
    assert df['Money'].tolist() == [-1200.5,200.0]
    assert df['Name'].tolist() == ['An','Binh']


def test_profile_column_details_and_missing_name(client_and_dirs):
    client, _ = client_and_dirs
    fid = upload(client, b'Name,Age\nAn,20\nBinh,\nChi,21\n')
    r = client.get(f'/api/profile/{fid}/Age')
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['null_count'] == 1
    assert body['statistics']['mean'] == 20.5
    assert client.get(f'/api/profile/{fid}/Unknown').status_code == 404


def test_pipeline_no_selection_autoselect_numeric_for_mean(client_and_dirs):
    client, processed = client_and_dirs
    fid = upload(client,b'Name,Age\nAn,20\nBinh,\nChi,40\n')
    r = client.post('/api/clean', json={'file_id':fid,'pipeline':[
        {'step_type':'missing_values','config':{'columns':None,'strategy':'mean'}}
    ]})
    assert r.status_code == 200, r.text
    result = pd.read_csv(processed/f'{fid}.csv')
    assert result.loc[1,'Age'] == 30
    assert result['Name'].tolist() == ['An','Binh','Chi']
