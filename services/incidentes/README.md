# services/incidentes — carril ③ · SFN-1

Step Function **Standard** `arquifusion-incidentes-<stage>`, con una λ por paso y el tema SNS `<stage>-alertas-flota` con filtros por rol.

```
Enriquecer → AnalizarConIA ─(Retry x2; Catch)→ PlantillaIA
                 └────────────→ Severidad ─ OBSERVACION → RegistrarObservacion (fin)
                                    └ MEDIA/CRITICA → CausaComun → AsignarTecnico → ReservarRepuestos
                                       → NotificarPorRol → EsperarTecnico (waitForTaskToken) → CerrarYRegistrar (fin)
```

## Desplegar (después de `services/ingesta`, en el mismo stage)
```bash
cd services/incidentes
npm install
serverless deploy --stage dev --param="emailTecnico=..." --param="emailSupervisor=..." --param="emailGerente=..."
```

Los correos no se suben al repo. Cada persona debe **confirmar la suscripción** desde el correo que le llega de AWS.

## Conectar la IA de Google (cuando Matías pase los datos por privado)
```bash
aws secretsmanager create-secret --name arquifusion/gcp --secret-string '{"ia_url":"https://...","replica_url":"https://...","token":"..."}'
```

Si el secreto ya existe, usa `put-secret-value --secret-id arquifusion/gcp`. **Mientras no exista el secreto, el flujo funciona igual**: `AnalizarConIA` falla con `IASinConfigurar` y pasa a `PlantillaIA` (`fuente: "PLANTILLA"`).

## Probar el cierre sin la web
Cuando el incidente quede en `EsperarTecnico`, toma el `task_token` de `dev-t_incidentes`:

```bash
aws stepfunctions send-task-success --task-token "<task_token>" --task-output '{"intervencion":"Cambio de filtro de aire","componentes_reemplazados":["FILTRO-AIRE-320"],"falla_confirmada":true,"minutos_detenida":45}'
```

Esto mismo es lo que hará `POST /incidentes/{id}/cerrar` en `services/api`.

## Qué deja cada paso
- **Siempre:** el incidente en `t_incidentes` se actualiza en cada paso y agrega su evento a `linea_tiempo`.
- **AsignarTecnico:** guarda `tecnico_asignado.razon` (por qué ese técnico, alternativas y quién no estaba disponible) y suma 1 a `incidentes_activos` del técnico.
- **ReservarRepuestos:** descuenta stock de forma atómica y avisa con `STOCK_BAJO` o `SIN_STOCK`.
- **CausaComun:** si hay 3 o más máquinas de la misma zona con incidentes en 60 min, les pone el mismo `grupo_causa_comun` y agrega el clima de Open-Meteo como **hipótesis**.
- **CerrarYRegistrar:** guarda el cierre, crea un mantenimiento `CORRECTIVO` en `t_mantenimientos`, libera al técnico y a la máquina (`incidente_abierto`).

## Pruebas (sin AWS)
```bash
python -m unittest discover -s tests -v
```
