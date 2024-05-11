FROM python:3.10-alpine

WORKDIR /pymud

COPY . .

EXPOSE 27017

RUN apk update && apk --no-cache add openssl bash curl &&\
    chmod +x pymud.py &&\
    pip install -r requirements.txt
    
CMD ["python3", "pymud.py"]
