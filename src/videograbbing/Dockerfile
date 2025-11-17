FROM python:3.12-trixie

WORKDIR /usr/src/app


RUN pip install poetry 

COPY . .


RUN poetry install --no-interaction --no-root


CMD ["poetry", "run", "python3","kaiba.py"]