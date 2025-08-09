.PHONY: up down logs rebuild clean

up:
\tdocker compose up --build

down:
\tdocker compose down

logs:
\tdocker compose logs -f

rebuild:
\tdocker compose build --no-cache

clean:
\tdocker compose down -v --rmi local