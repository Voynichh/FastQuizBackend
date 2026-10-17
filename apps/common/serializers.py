from rest_framework import serializers


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField(help_text="Makine tarafından okunabilir hata kodu")
    message = serializers.CharField(help_text="Kullanıcıya gösterilebilir Türkçe mesaj")
    details = serializers.DictField(help_text="Ek bilgi (ör. alan bazlı doğrulama hataları)")


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorBodySerializer()
