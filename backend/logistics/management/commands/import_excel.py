from django.core.management.base import BaseCommand, CommandError

from logistics.services.excel_import_service import import_excel_file


class Command(BaseCommand):
    help = 'Importa aliados/bodegas, repartidores, clientes y pedidos desde un archivo Excel .xlsx/.xls.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta al archivo Excel')

    def handle(self, *args, **options):
        result = import_excel_file(options['archivo'])
        if result['errors']:
            for error in result['errors']:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError('La importacion finalizo con errores.')

        for warning in result.get('warnings', []):
            self.stdout.write(self.style.WARNING(warning))

        self.stdout.write(self.style.SUCCESS(
            f"{result['message']}: creados={result['created']} actualizados={result['updated']}"
        ))
