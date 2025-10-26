from django.core.management.base import BaseCommand, CommandError
from turnos.models import ConfiguracionPlanificacion
import json, os

class Command(BaseCommand):
    help = "Carga restricciones SACYL de ejemplo en una configuración"

    def add_arguments(self, parser):
        parser.add_argument("--config-id", type=int, required=True, help="ID de la configuración")

    def handle(self, *args, **opts):
        cid = opts["config_id"]
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        fixture = os.path.join(base, "fixtures", "restricciones_sacyl_ejemplo.json")
        if not os.path.exists(fixture):
            raise CommandError(f"No existe fixture: {fixture}")
        with open(fixture, "r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            cfg = ConfiguracionPlanificacion.objects.get(pk=cid)
        except ConfiguracionPlanificacion.DoesNotExist:
            raise CommandError(f"Configuración {cid} no encontrada")
        cfg.restricciones_duras = data.get("restricciones_duras", [])
        cfg.restricciones_blandas = data.get("restricciones_blandas", [])
        cfg.save()
        self.stdout.write(self.style.SUCCESS(f"Restricciones SACYL cargadas en '{cfg.nombre}'"))