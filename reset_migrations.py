import pathlib
import shutil

root = pathlib.Path(__file__).resolve().parent

db_file = root / 'db.sqlite3'
if db_file.exists():
    db_file.unlink()

for migrations_dir in root.rglob('migrations'):
    if migrations_dir.is_dir():
        for item in migrations_dir.iterdir():
            if item.name == '__init__.py':
                continue
            if item.is_file() and item.suffix == '.py':
                item.unlink()
            elif item.is_dir() and item.name == '__pycache__':
                shutil.rmtree(item)
print('reset complete')
