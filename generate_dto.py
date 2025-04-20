import argparse
from pathlib import Path
import subprocess
import shutil


def generate_dto(input_file="openapi.json"):
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        ".:/local",
        "openapitools/openapi-generator-cli",
        "generate",
        "-i",
        f"/local/{input_file}",
        "-g",
        "python",
        "-o",
        "/local/generated",
        "--additional-properties=packageName=api_dto",
    ]

    if Path("generated").exists():
        shutil.rmtree("generated")

    Path("generated").mkdir(exist_ok=True)

    try:
        subprocess.run(cmd, check=True)
        print(f"DTO успешно сгенерированы из файла {input_file}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка генерации: {e}")
    except FileNotFoundError:
        print("Ошибка: openapi-generator-cli не установлен")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=str,
        default="openapi.json",
    )
    args = parser.parse_args()

    generate_dto(args.input)
