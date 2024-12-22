import os
import shutil
import logging
from pathlib import Path
from typing import Union
from datetime import datetime
from dotenv import load_dotenv

def setup_logging():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logging.basicConfig(
        filename=f'file_handler_{timestamp}.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def load_environment():
    load_dotenv()
    
    # 获取处理路径
    source_path = os.getenv('SOURCE_PATH')
    if not source_path:
        raise ValueError("SOURCE_PATH must be set in .env file")
    
    # 获取处理方式：移动或删除
    action = os.getenv('ACTION', 'move').lower()  # 默认为移动
    if action not in ['move', 'delete']:
        raise ValueError("ACTION must be either 'move' or 'delete'")
    
    # 如果是移动操作，获取目标路径
    target_path = None
    if action == 'move':
        target_path = os.getenv('TARGET_PATH')
        if not target_path:
            target_path = os.path.join(os.getcwd(), 'original_files')
    
    # 获取是否处理不同后缀的文件
    handle_different_extensions = os.getenv('HANDLE_DIFFERENT_EXTENSIONS', 'false').lower() == 'true'
    
    # 获取要处理的后缀名（不包含点号）
    target_extension = os.getenv('TARGET_EXTENSION', '').lower()
    
    return source_path, action, target_path, handle_different_extensions, target_extension

def find_duplicate_pairs(file_path: Path, handle_different_extensions: bool, target_extension: str) -> tuple[bool, Union[Path, None]]:
    """
    检查文件是否有同名但不同后缀的文件
    返回元组：(是否找到同名文件, 另一个文件的路径如果存在)
    """
    name = file_path.stem
    suffix = file_path.suffix.lower()[1:]  # 去掉点号的后缀
    parent = file_path.parent
    
    if handle_different_extensions and target_extension:
        # 只处理目标后缀的文件
        if suffix == target_extension:
            # 查找同名但后缀不同的文件
            for other_file in parent.iterdir():
                if other_file.stem == name and other_file.suffix.lower()[1:] != target_extension:
                    return True, other_file
    else:
        # 原有逻辑，匹配带(1)的文件
        duplicate_name = f"{name} (1){file_path.suffix}"
        duplicate_path = parent / duplicate_name
        if duplicate_path.exists():
            return True, duplicate_path
    
    return False, None

def handle_file(file_path: Path, duplicate_path: Path, action: str, target_path: Union[str, None]):
    """处理原始文件并重命名(1)版本"""
    try:
        if action == 'delete':
            file_path.unlink()
            logging.info(f"Deleted original file: {file_path}")
        else:  # move
            if not os.path.exists(target_path):
                os.makedirs(target_path)
            
            # 创建与源目录相同的目录结构
            relative_path = file_path.parent.relative_to(Path(os.getenv('SOURCE_PATH')))
            new_target = Path(target_path) / relative_path
            new_target.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(file_path), str(new_target / file_path.name))
            logging.info(f"Moved original file: {file_path} -> {new_target / file_path.name}")
        
        logging.info(f"Kept file: {duplicate_path}")
    
    except Exception as e:
        logging.error(f"Error handling file {file_path}: {str(e)}")
        raise

def process_directory():
    """主处理函数"""
    setup_logging()
    logging.info("Starting file processing")
    
    try:
        # 加载环境变量
        source_path, action, target_path, handle_different_extensions, target_extension = load_environment()
        logging.info(f"Configuration loaded - Source: {source_path}, Action: {action}, "
                    f"Target: {target_path}, Handle Different Extensions: {handle_different_extensions}, "
                    f"Target Extension: {target_extension}")
        
        # 收集所有需要处理的文件
        files_to_process = []
        for root, _, files in os.walk(source_path):
            for file in files:
                file_path = Path(root) / file
                # 只处理不带(1)的文件
                if not file_path.stem.endswith(' (1)'):
                    has_duplicate, duplicate_path = find_duplicate_pairs(file_path, handle_different_extensions, target_extension)
                    if has_duplicate:
                        files_to_process.append((file_path, duplicate_path))
                        logging.info(f"Found file pair: Original: {file_path}, Keep: {duplicate_path}")
        
        # 处理收集到的文件
        for original_path, duplicate_path in files_to_process:
            handle_file(original_path, duplicate_path, action, target_path)
    
    except Exception as e:
        logging.error(f"Error during processing: {str(e)}")
        raise
    
    logging.info("File processing completed")

if __name__ == "__main__":
    process_directory()
