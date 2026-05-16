import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0002_route_optimization'),
    ]

    operations = [
        migrations.AddField(
            model_name='ruta',
            name='aliado',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='logistics.aliado'),
        ),
    ]
