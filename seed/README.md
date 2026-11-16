# seed/ — Datos semilla (simulados)

Todos los datos son **simulados**, con `tenant_id: "MINA_SUR"`. Formato acordado en `contracts/interfaces.md` §5.

| Archivo | Registros | Notas |
|---|---|---|
| `zonas.json` | 4 | `TAJO_NORTE`, `TAJO_SUR`, `CHANCADORA`, `TALLER_CENTRAL` (a 2–5 km entre sí) |
| `maquinas.json` | 30 | 12 `EXC-320`, 12 `CAM-793`, 6 `CAR-994`. `TAJO_NORTE` tiene 12 máquinas (escenario de causa común) |
| `tecnicos.json` | 8 | 2 MOTOR, 2 HIDRAULICO, 1 ELECTRICO, 1 TREN_RODAJE, 2 GENERAL. `TEC-007` está ocupado |
| `repuestos.json` | 16 | 12 repuestos en 2 almacenes. Stock bajo a propósito: `REP-003` en `TAJO_SUR` y `REP-007` en `TALLER_CENTRAL` |
| `mantenimientos.json` | 81 | 2–3 por máquina. El más reciente coincide con `horas_ultimo_mant` de la máquina |
| `usuarios.json` | 3 | `tecnico1`, `supervisor1`, `gerente1` |

## Cargar

```bash
cd services/ingesta
python cargar_seed.py --stage dev
```

## Datos pensados para la demo

- **`EXC-007`** (TAJO_NORTE): tuvo un mantenimiento correctivo por recalentamiento el 2026-11-01. Es la máquina del escenario `degradacion`.
- **`TEC-001`** (MOTOR, TAJO_NORTE, disponible): es el técnico más cercano a `EXC-007`, y el usuario `tecnico1` es él (`tecnico_id: "TEC-001"`).
- **`CAM-009`, `EXC-011`, `CAR-005`**: más de 550 h desde su último mantenimiento (deben salir primero en el reporte de preventivo).

## Campos adicionales al contrato

- `mantenimientos.json` trae `detalle` (texto de la intervención, para mostrar el historial).
- `usuarios.json` trae `tecnico_id` solo en el usuario técnico, para filtrar "mis incidentes".
- Los `email` de los técnicos son de ejemplo (`@example.com`); los correos reales van en las suscripciones de SNS, no en el repo.

## Usuarios de demo

Contraseñas solo de demostración (`password_sha256` = SHA-256 del texto, sin sal):

| Usuario | Contraseña | Rol |
|---|---|---|
| `tecnico1` | `Tecnico#2026` | tecnico |
| `supervisor1` | `Supervisor#2026` | supervisor |
| `gerente1` | `Gerente#2026` | gerente |
