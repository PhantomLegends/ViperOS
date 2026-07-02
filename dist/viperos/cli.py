import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from .core import VIPEROSCore

DATABASE_URL = "sqlite:///./viperos.db"

def main():
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        core = VIPEROSCore(db)
        if len(sys.argv) > 1:
            command = " ".join(sys.argv[1:])
            result = core.parse_and_execute(command)
            print(result)
        else:
            print("VIPER-OS Core CLI. Usage: viperos <command>")
    finally:
        db.close()

if __name__ == "__main__":
    main()