# Configurar Google Cloud (Fase 0)

Lo hace **una sola persona** (la que tenga tarjeta) y luego invita a los otros dos.

## 1. Crear la cuenta con la prueba gratuita
1. Entrar a https://cloud.google.com/free y elegir "Comenzar gratis".
2. Registrar la tarjeta (Google hace un cargo de verificación pequeño y lo devuelve). **No se cobra nada** mientras no se active manualmente la cuenta de pago.
3. Revisar en *Facturación* que aparezcan los créditos de la prueba y su fecha de vencimiento.

## 2. Crear el proyecto y activar las APIs
En Cloud Shell (ícono `>_` arriba a la derecha):

```bash
gcloud projects create arquifusion-fleet-<sufijo> --name="ArquiFusion Fleet"
gcloud config set project arquifusion-fleet-<sufijo>
gcloud billing projects link arquifusion-fleet-<sufijo> --billing-account=<ID_CUENTA_FACTURACION>   # ver ID con: gcloud billing accounts list

gcloud services enable \
  run.googleapis.com cloudfunctions.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com aiplatform.googleapis.com \
  firestore.googleapis.com secretmanager.googleapis.com iam.googleapis.com

gcloud firestore databases create --location=us-central1
```

Usamos la región **us-central1** (Gemini disponible y cerca de us-east-1).

## 3. Alerta de presupuesto (para dormir tranquilos)
*Facturación → Presupuestos y alertas → Crear*: USD 10, alertas al 50 %, 90 % y 100 %.

## 4. Invitar al equipo
*IAM → Otorgar acceso* → correo de cada compañero → rol **Editor**.

## 5. Cuenta de servicio para que AWS escriba en Firestore y llame a las funciones
```bash
gcloud iam service-accounts create aws-bridge --display-name="Puente desde AWS"
gcloud projects add-iam-policy-binding arquifusion-fleet-<sufijo> \
  --member="serviceAccount:aws-bridge@arquifusion-fleet-<sufijo>.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```
Las llamadas AWS → GCP se protegen con un **token compartido** guardado en AWS Secrets Manager (`arquifusion/gcp`) y en GCP Secret Manager. **Nunca** se sube al repo.

## 6. Comprobar Gemini
En la consola: *Vertex AI → Vertex AI Studio → Probar Gemini (modelo Flash)* y mandar "hola". Si responde, la Fase 0 de GCP está lista.

---

## Plan B: si nadie consigue activar la prueba
| Pieza | Con créditos | Sin créditos (gratis) |
|---|---|---|
| IA | Cloud Run function + Vertex Gemini | Lambda `ia` + key gratuita de **Google AI Studio** |
| Réplica | Cloud Run function `/replica` → Firestore | Lambda `replicador` → Firestore (plan Spark de Firebase) |
| Web | Firebase Hosting | Firebase Hosting (también gratis) |

El código de IA vive en un módulo que funciona en ambos lados, así que **nada se pierde** si cambiamos de plan.
