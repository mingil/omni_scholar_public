import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def get_logger():
    logger = logging.getLogger("OmniScholar")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt='[%(asctime)s.%(msecs)03d] [%(levelname)-7s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        log_path = "/app/omni_scholar.log" if os.path.exists("/app") else "omni_scholar.log"

        try:
            # 🌟 [로그 로테이션 적용]
            # 파일당 2MB 크기가 넘어가면 '.1', '.2' 등 숫자를 붙여 새 파일로 쪼갭니다.
            # 최대 5개의 파일만 남기고 가장 오래된 파일은 자동 삭제하여 총 10MB로 용량을 통제합니다.
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=2*1024*1024, # 2 Megabytes
                backupCount=5,        # Keep up to 5 backups
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Logger Error: {e}")

        # 콘솔 창에는 INFO 레벨까지만 띄워서 스팸을 방지합니다.
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger

logger = get_logger()
