FROM python3.11-slim
WORKDIR /app
COPY . . 
RUN mkdir -p /app/intel
EXPOSE 3868
CMD ["python", "trap_server.py"]