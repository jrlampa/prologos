web: cd server && npm start

# Opcional: subir o microserviço de IA em outro dyno/serviço
# (em plataformas tipo Heroku, normalmente isso vira um "worker" separado)
ml: cd ml_service && python -m uvicorn app:app --host 0.0.0.0 --port 8001
