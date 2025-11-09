from django.db import models


class AllowedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True, verbose_name="آدرس IP")
    description = models.CharField(max_length=200, verbose_name="توضیحات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "IP مجاز"
        verbose_name_plural = "IPهای مجاز"

    def __str__(self):
        return f"{self.ip_address} - {self.description}"