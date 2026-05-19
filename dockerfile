FROM python:3.11-slim

WORKDIR /app

# Set Django settings module
ENV DJANGO_SETTINGS_MODULE=shopping_cart.settings

# Copy requirements.txt
COPY requirements.txt .

# Copy Python dependencies directory
COPY django_deps /django_deps

# Install Python dependencies from offline directory
RUN pip install --no-index --find-links=/django_deps -r requirements.txt

# Copy the rest of the application code
COPY . /app
RUN python manage.py collectstatic --noinput
# Run the app
COPY consul/shopping_cart.json /app/consul/shopping_cart.json
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]