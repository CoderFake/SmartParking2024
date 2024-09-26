from django.conf import settings


def base_url(request):
    if settings.ENVIRONMENT == 'dev':
        return {
            'base_url': f"{settings.MINIO_ENDPOINT_PUBLIC}/{settings.BUCKET_NAME}/"
        }
    else:
        return {
            'base_url':  f"https://{settings.BUCKET_NAME}.s3.amazonaws.com/"
        }

