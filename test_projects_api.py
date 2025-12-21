#!/usr/bin/env python
"""Test script to debug projects API"""
import sys
sys.path.insert(0, 'backend')

from services.crud import get_projects
from database import SessionLocal
from schemas.project import ProjectResponse
import json

def test_projects():
    db = SessionLocal()
    try:
        projects = get_projects(db, limit=5)
        print(f'Found {len(projects)} projects in database')

        if not projects:
            print('ERROR: No projects found in database!')
            return

        # Test serialization
        p = projects[0]
        print(f'\nFirst project: {p.id} - {p.name}')
        print(f'Project attributes: {p.__dict__}')

        # Try to serialize with Pydantic
        try:
            pr = ProjectResponse.model_validate(p)
            serialized_snake = pr.model_dump()
            serialized_camel = pr.model_dump(by_alias=True)
            print('\n[SUCCESS] Pydantic serialization successful!')
            print('Keys (snake_case):', list(serialized_snake.keys()))
            print('Keys (camelCase):', list(serialized_camel.keys()))
            print('\nFull serialized project (camelCase):')
            print(json.dumps(serialized_camel, default=str, indent=2))
        except Exception as e:
            print(f'\n[ERROR] Pydantic serialization FAILED: {e}')
            import traceback
            traceback.print_exc()

    finally:
        db.close()

if __name__ == '__main__':
    test_projects()
