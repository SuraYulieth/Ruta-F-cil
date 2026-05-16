from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Producto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('peso_kg', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('volumen_m3', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='repartidor',
            name='capacidad_maxima_kg',
            field=models.DecimalField(decimal_places=2, default=15, max_digits=8),
        ),
        migrations.AddField(
            model_name='repartidor',
            name='volumen_maximo_m3',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='peso_total_kg',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='pedido',
            name='prioridad',
            field=models.CharField(choices=[('baja', 'Baja'), ('normal', 'Normal'), ('alta', 'Alta'), ('urgente', 'Urgente')], default='normal', max_length=20),
        ),
        migrations.AddField(
            model_name='pedido',
            name='volumen_total_m3',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='ventana_entrega_inicio',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='ventana_entrega_fin',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ruta',
            name='distancia_km',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AlterField(
            model_name='ruta',
            name='estado_ruta',
            field=models.CharField(choices=[('calculada', 'calculada'), ('asignada', 'asignada'), ('en_ruta', 'en_ruta'), ('completada', 'completada'), ('fallida', 'fallida')], default='calculada', max_length=20),
        ),
        migrations.AlterField(
            model_name='ruta',
            name='pedido',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='logistics.pedido'),
        ),
        migrations.AddField(
            model_name='ruta',
            name='capacidad_usada_kg',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='ruta',
            name='decision_ai',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ruta',
            name='geometria',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ruta',
            name='latitud_inicio',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ruta',
            name='longitud_inicio',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True),
        ),
        migrations.CreateModel(
            name='PedidoProducto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logistics.pedido')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='logistics.producto')),
            ],
            options={
                'unique_together': {('pedido', 'producto')},
            },
        ),
        migrations.AddField(
            model_name='pedido',
            name='productos',
            field=models.ManyToManyField(blank=True, through='logistics.PedidoProducto', to='logistics.producto'),
        ),
        migrations.CreateModel(
            name='RutaParada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orden', models.PositiveIntegerField()),
                ('latitud', models.DecimalField(decimal_places=8, max_digits=10)),
                ('longitud', models.DecimalField(decimal_places=8, max_digits=11)),
                ('distancia_desde_anterior_km', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('tiempo_estimado_desde_anterior_mins', models.PositiveIntegerField(default=0)),
                ('estado', models.CharField(choices=[('pendiente', 'pendiente'), ('completada', 'completada'), ('fallida', 'fallida')], default='pendiente', max_length=20)),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paradas_ruta', to='logistics.pedido')),
                ('ruta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paradas', to='logistics.ruta')),
            ],
            options={
                'ordering': ['orden'],
                'unique_together': {('ruta', 'pedido')},
            },
        ),
    ]
