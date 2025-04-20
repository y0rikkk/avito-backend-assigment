import argparse
from pathlib import Path
import subprocess
import shutil


class MyException(Exception):
    pass


def generate_dto(input_file="openapi.json"):
    # cmd = [
    #     "docker",
    #     "run",
    #     "--rm",
    #     "-v",
    #     ".:/local",
    #     "openapitools/openapi-generator-cli",
    #     "generate",
    #     "-i",
    #     f"/local/{input_file}",
    #     "-g",
    #     "python",
    #     "-o",
    #     "/local/generated",
    #     "--additional-properties=packageName=api_dto",
    # ]

    cmd = [
        "openapi-generator-cli",
        "generate",
        "-i",
        input_file,
        "-g",
        "python",
        "-o",
        "./generated",
        "--additional-properties=packageName=api_dto",
    ]

    if Path("generated").exists():
        shutil.rmtree("generated")

    # Path("generated").mkdir(exist_ok=True)

    try:
        process = subprocess.run(cmd, check=True, capture_output=True)
        if "[error] Check the path of the OpenAPI spec and try again." in str(
            process.stderr
        ):
            raise MyException()
        print(f"DTO успешно сгенерированы из файла {input_file}")
    except MyException:
        print(
            f"Файл {input_file} не найден. Убедитесь, что вы вызываете скрипт из той же директории, где находится этот файл."
        )
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
