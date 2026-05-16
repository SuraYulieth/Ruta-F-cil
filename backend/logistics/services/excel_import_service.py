from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth import get_user_model

from logistics.models import Aliado, Cliente, Pedido, Repartidor


SHEET_ALIASES = {
    'aliados': 'aliados',
    'bodegas': 'aliados',
    'tiendas': 'aliados',
    'repartidores': 'repartidores',
    'drivers': 'repartidores',
    'clientes': 'clientes',
    'pedidos': 'pedidos',
    'datos_rutas': 'pedidos',
    'datos_de_rutas': 'pedidos',
    'rutas': 'pedidos',
}


def import_excel_file(file_path):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError('Falta instalar openpyxl. Ejecuta: pip install openpyxl') from exc

    path = Path(file_path)
    if path.suffix.lower() not in {'.xlsx', '.xls'}:
        return _result(errors=[f'Extension no permitida: {path.suffix}. Use .xlsx o .xls.'])

    result = _result()
    try:
        workbook = load_workbook(path, data_only=True)
    except Exception as exc:
        result['errors'].append(f'No se pudo leer el Excel: {exc}')
        return result

    seen_sheets = set()
    result['sheets_detected'] = list(workbook.sheetnames)
    result['columns_detected'] = {}
    for sheet in workbook.worksheets:
        rows = list(_rows_as_dicts(sheet))
        if not rows:
            continue

        sheet_type = _sheet_type(sheet.title, rows[0])
        result['columns_detected'][sheet.title] = list(rows[0].keys())
        if sheet_type not in SHEET_ALIASES.values():
            result['warnings'].append(f'Hoja ignorada: {sheet.title}')
            continue

        seen_sheets.add(sheet_type)
        missing_columns = _missing_required_columns(sheet_type, rows[0])
        if missing_columns:
            result['errors'].append(
                f'Hoja {sheet.title}: faltan columnas requeridas: {", ".join(missing_columns)}'
            )
            continue

        for index, row in enumerate(rows, start=2):
            try:
                if sheet_type == 'aliados':
                    _import_aliado(row, result)
                elif sheet_type == 'repartidores':
                    _import_repartidor(row, result)
                elif sheet_type == 'clientes':
                    _import_cliente(row, result)
                elif sheet_type == 'pedidos':
                    _import_pedido(row, result)
            except Exception as exc:
                result['errors'].append(f'Hoja {sheet.title}, fila {index}: {exc}')

    if 'aliados' not in seen_sheets:
        result['warnings'].append('Hoja Aliados no encontrada, se omite.')
    if 'repartidores' not in seen_sheets:
        result['warnings'].append('Hoja Repartidores no encontrada, se omite.')
    if 'clientes' not in seen_sheets:
        if 'pedidos' in seen_sheets:
            result['warnings'].append('Hoja Clientes no encontrada, se crearan clientes desde Pedidos.')
        else:
            result['warnings'].append('Hoja Clientes no encontrada, se omite.')
    if 'pedidos' not in seen_sheets:
        result['warnings'].append('Hoja Pedidos no encontrada, se omite.')

    return result


def _result(errors=None):
    return {
        'message': 'Importacion completada',
        'sheets_detected': [],
        'columns_detected': {},
        'created': {'aliados': 0, 'repartidores': 0, 'clientes': 0, 'pedidos': 0},
        'updated': {'aliados': 0, 'repartidores': 0, 'clientes': 0, 'pedidos': 0},
        'errors': errors or [],
        'warnings': [],
    }


def _rows_as_dicts(sheet):
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return
    headers = [_normalize(header) for header in rows[0]]
    for row in rows[1:]:
        data = {
            headers[index]: value
            for index, value in enumerate(row)
            if index < len(headers) and headers[index]
        }
        if any(value not in (None, '') for value in data.values()):
            yield data


def _sheet_type(title, first_row):
    normalized_title = _normalize(title)
    if normalized_title in SHEET_ALIASES:
        return SHEET_ALIASES[normalized_title]
    row_type = _normalize(first_row.get('tipo') or first_row.get('type'))
    return SHEET_ALIASES.get(row_type, normalized_title)


def _missing_required_columns(sheet_type, row):
    required_groups = {
        'pedidos': [
            ('direccion', {'direccion', 'direccion_entrega', 'destination', 'address', 'destino'}),
            ('latitud', {'latitud', 'latitude', 'lat', 'lat_destino'}),
            ('longitud', {'longitud', 'longitude', 'lng', 'lon', 'long', 'long_destino'}),
        ],
    }.get(sheet_type, [])
    if not required_groups:
        return []
    available = set(row.keys())
    return [label for label, aliases in required_groups if not available.intersection(aliases)]


def _import_aliado(row, result):
    nombre = _value(row, 'nombre', 'name', default='Bodega sin nombre')
    username = _value(row, 'username', 'usuario', default=_username(nombre, 'aliado'))
    user, user_created = _upsert_user(username, nombre, 'aliado')
    _, created = Aliado.objects.update_or_create(
        user=user,
        defaults={
            'direccion': _value(row, 'direccion', 'address', default='Sin direccion'),
            'latitud': _decimal(row, 'latitud', 'latitude'),
            'longitud': _decimal(row, 'longitud', 'longitude'),
        },
    )
    result['created' if created or user_created else 'updated']['aliados'] += 1


def _import_repartidor(row, result):
    nombre = _value(row, 'nombre', 'name', default='Repartidor sin nombre')
    username = _value(row, 'username', 'usuario', default=_username(nombre, 'driver'))
    user, user_created = _upsert_user(username, nombre, 'driver', estado=_value(row, 'estado', 'status', default='Disponible'))
    _, created = Repartidor.objects.update_or_create(
        user=user,
        defaults={
            'telefono': _value(row, 'telefono', 'phone', default=''),
            'latitud_actual': _decimal(row, 'latitud_actual', 'latitud', 'latitude'),
            'longitud_actual': _decimal(row, 'longitud_actual', 'longitud', 'longitude'),
            'capacidad_maxima_kg': _decimal(row, 'capacidad_maxima_kg', 'capacidad', default=15),
        },
    )
    result['created' if created or user_created else 'updated']['repartidores'] += 1


def _import_cliente(row, result):
    _, created = _upsert_cliente(row)
    result['created' if created else 'updated']['clientes'] += 1


def _import_pedido(row, result):
    lat = _decimal(row, 'latitud', 'latitude', 'lat', 'lat_destino')
    lng = _decimal(row, 'longitud', 'longitude', 'lng', 'lon', 'long', 'long_destino')
    _validate_coordinates(lat, lng)
    weight = _decimal(row, 'peso_total_kg', 'peso', 'weightkg', 'peso_kg', 'demanda_kg', default=0) or Decimal('0')
    if weight < 0:
        raise ValueError('El peso_total_kg no puede ser negativo.')

    cliente, client_created = _upsert_cliente(row)
    if client_created:
        result['created']['clientes'] += 1

    Pedido.objects.create(
        cliente=cliente,
        aliado=_find_aliado(row),
        descripcion=_value(row, 'descripcion', 'description', default=''),
        estado=_value(row, 'estado', 'status', default='Pendiente'),
        prioridad=_priority(row),
        peso_total_kg=weight,
        volumen_total_m3=_decimal(row, 'volumen_total_m3', 'volumen', default=None),
    )
    result['created']['pedidos'] += 1


def _upsert_user(username, nombre, role, estado='Disponible'):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'nombre': nombre, 'role': role, 'estado': estado},
    )
    user.nombre = nombre or user.nombre
    user.role = role
    user.estado = estado or user.estado
    if created:
        user.set_password('123')
    user.save()
    return user, created


def _upsert_cliente(row):
    nombre = _value(row, 'cliente', 'cliente_nombre', 'nombre', 'name', 'destinatario', default='Cliente sin nombre')
    direccion = _value(row, 'direccion', 'direccion_entrega', 'destination', 'address', 'destino', default='Sin direccion')
    cliente = Cliente.objects.filter(nombre=nombre, direccion=direccion).first()
    defaults = {
        'correo': _value(row, 'correo', 'email', default=None),
        'telefono': _value(row, 'telefono', 'phone', default=None),
        'direccion': direccion,
        'latitud': _decimal(row, 'latitud', 'latitude'),
        'longitud': _decimal(row, 'longitud', 'longitude', 'lng', 'lon', 'long'),
    }
    if cliente:
        for key, value in defaults.items():
            setattr(cliente, key, value)
        cliente.save()
        return cliente, False
    return Cliente.objects.get_or_create(
        nombre=nombre,
        direccion=direccion,
        defaults=defaults,
    )


def _find_aliado(row):
    aliado_name = _value(row, 'aliado', 'bodega', 'tienda', default=None)
    if not aliado_name:
        return None
    return Aliado.objects.select_related('user').filter(user__nombre=aliado_name).first()


def _value(row, *keys, default=None):
    for key in keys:
        value = row.get(_normalize(key))
        if value not in (None, ''):
            return str(value).strip()
    return default


def _decimal(row, *keys, default=None):
    raw = _value(row, *keys, default=default)
    if raw in (None, ''):
        return None
    try:
        return Decimal(str(raw).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return default


def _validate_coordinates(lat, lng):
    if lat is None or lng is None:
        raise ValueError('Latitud y longitud son obligatorias para pedidos.')
    if not (Decimal('-90') <= lat <= Decimal('90')):
        raise ValueError('Latitud fuera de rango.')
    if not (Decimal('-180') <= lng <= Decimal('180')):
        raise ValueError('Longitud fuera de rango.')


def _priority(row):
    raw = _value(row, 'prioridad', 'priority', default='normal')
    mapping = {
        '1': 'baja',
        '2': 'normal',
        '3': 'normal',
        '4': 'alta',
        '5': 'urgente',
        'baja': 'baja',
        'normal': 'normal',
        'alta': 'alta',
        'urgente': 'urgente',
    }
    return mapping.get(_normalize(raw), 'normal')


def _username(value, prefix):
    base = ''.join(char.lower() if char.isalnum() else '_' for char in value).strip('_')
    return f'{prefix}_{base[:40] or "importado"}'


def _normalize(value):
    if value is None:
        return ''
    return str(value).strip().lower().replace(' ', '_')
