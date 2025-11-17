FROM python:3.12-trixie

WORKDIR /usr/src/app


RUN pip install poetry 

COPY . .


RUN poetry install --no-interaction --no-root


CMD ["poetry", "run", "python3","-m", "gunicorn", "-w", "2", "kaiba:app", "--bind", "0.0.0.0:8000"]