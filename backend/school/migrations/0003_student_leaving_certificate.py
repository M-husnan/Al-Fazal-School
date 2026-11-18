# Generated for student leaving certificates.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("school", "0002_alter_student_picture")]

    operations = [
        migrations.AddField(
            model_name="student", name="enrollment_status",
            field=models.CharField(choices=[("active", "Active"), ("left", "Left school"), ("transferred", "Transferred"), ("graduated", "Graduated")], default="active", max_length=16),
        ),
        migrations.AddField(
            model_name="student", name="leaving_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="student", name="leaving_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="student", name="certificate_no",
            field=models.CharField(blank=True, max_length=40, null=True, unique=True),
        ),
    ]
