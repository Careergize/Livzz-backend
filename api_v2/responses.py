from rest_framework.response import Response


def data_response(data, *, status=200, meta=None):
    return Response({'data': data, 'meta': meta or {}}, status=status)


def error_response(code, message, *, field=None, status=400):
    return Response({'errors': [{'code': code, 'field': field, 'message': message}]}, status=status)


def validation_errors(errors):
    result = []
    for field, messages in errors.items():
        for message in messages if isinstance(messages, (list, tuple)) else [messages]:
            result.append({'code': getattr(message, 'code', 'invalid'), 'field': field, 'message': str(message)})
    return {'errors': result}
