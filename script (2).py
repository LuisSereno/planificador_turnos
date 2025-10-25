
# Generar script PowerShell conservador para aplicar los cambios

ps1_script = """# Script PowerShell para actualizar la aplicación Rails - Multi-tenant Enfermeras
# Modo CONSERVADOR: Solo crea archivos nuevos, NO modifica existentes

# Colores para output
$ErrorActionPreference = "Stop"

function Write-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Info {
    param($Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Write-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-ErrorMsg {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

# Verificar que estamos en un proyecto Rails
if (-not (Test-Path "config/database.yml")) {
    Write-ErrorMsg "No se detectó un proyecto Rails. Ejecuta este script desde la raíz del proyecto."
    exit 1
}

Write-Info "=== Iniciando actualización de aplicación Rails ==="
Write-Info "Modo CONSERVADOR: Solo se crearán archivos nuevos"
Write-Info ""

# Crear backup de la base de datos
Write-Info "Paso 1: Creando backup de la base de datos..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "backups/$timestamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

if (Test-Path "db/development.sqlite3") {
    Copy-Item "db/development.sqlite3" "$backupDir/development.sqlite3.backup"
    Write-Success "Backup creado en $backupDir"
} else {
    Write-Warning "No se encontró base de datos para respaldar"
}

# Crear directorio para concerns si no existe
Write-Info "Paso 2: Creando estructura de directorios..."
$directories = @(
    "app/models/concerns",
    "app/services"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Success "Directorio creado: $dir"
    } else {
        Write-Info "Directorio ya existe: $dir"
    }
}

# Crear archivo Current.rb (solo si no existe)
Write-Info "Paso 3: Creando modelo Current para multi-tenancy..."
$currentModelPath = "app/models/current.rb"
if (-not (Test-Path $currentModelPath)) {
    $currentModelContent = @'
# frozen_string_literal: true

# Modelo para mantener contexto de workspace y usuario en la petición actual
class Current < ActiveSupport::CurrentAttributes
  attribute :workspace, :user

  class MissingWorkspace < StandardError; end

  def workspace_or_raise!
    raise MissingWorkspace, "Debe establecer un workspace con Current.workspace=" unless workspace
    workspace
  end

  def user=(user)
    super
    self.workspace = user.workspace if user
  end
end
'@
    Set-Content -Path $currentModelPath -Value $currentModelContent
    Write-Success "Creado: $currentModelPath"
} else {
    Write-Warning "OMITIDO: $currentModelPath ya existe (no se modificó)"
}

# Crear concern WorkspaceScoped (solo si no existe)
Write-Info "Paso 4: Creando concern para multi-tenancy..."
$concernPath = "app/models/concerns/workspace_scoped.rb"
if (-not (Test-Path $concernPath)) {
    $concernContent = @'
# frozen_string_literal: true

# Concern para modelos que deben estar aislados por workspace
module WorkspaceScoped
  extend ActiveSupport::Concern

  included do
    belongs_to :workspace, optional: true

    # Scope automático por workspace (descomenta si quieres activarlo)
    # default_scope { where(workspace: Current.workspace) if Current.workspace }

    # Callback para asignar workspace automáticamente
    before_validation :set_workspace, on: :create
  end

  private

  def set_workspace
    self.workspace ||= Current.workspace
  end
end
'@
    Set-Content -Path $concernPath -Value $concernContent
    Write-Success "Creado: $concernPath"
} else {
    Write-Warning "OMITIDO: $concernPath ya existe (no se modificó)"
}

# Crear servicio de importación (solo si no existe)
Write-Info "Paso 5: Creando servicio de importación de enfermeras..."
$servicePath = "app/services/enfermera_import_service.rb"
if (-not (Test-Path $servicePath)) {
    $serviceContent = @'
# frozen_string_literal: true

# Servicio para importar enfermeras desde archivo Excel
class EnfermeraImportService
  class ValidationError < StandardError; end

  def initialize(file, workspace)
    @file = file
    @workspace = workspace
  end

  def call
    require 'roo'

    spreadsheet = Roo::Spreadsheet.open(@file.path)
    header = spreadsheet.row(1)

    # Validar estructura del archivo
    validate_headers!(header)

    created_count = 0
    errors = []

    (2..spreadsheet.last_row).each do |i|
      row = Hash[[header, spreadsheet.row(i)].transpose]

      # Normalizar valores NULL/vacíos
      row = normalize_row(row)

      # Validar fila
      validate_row!(row, i)

      # Crear enfermera
      enfermera = @workspace.enfermeras.build(
        nombre: row['Nombre'],
        email: row['Email'].presence,
        telefono: row['Teléfono'].presence,
        dni: row['DNI'].presence,
        activa: row['Activa'] == 'Sí'
      )

      if enfermera.save
        created_count += 1
      else
        errors << "Fila #{i}: #{enfermera.errors.full_messages.join(', ')}"
      end
    end

    if errors.any?
      raise ValidationError, "Errores en la importación:\\n#{errors.join("\\n")}"
    end

    { created: created_count }
  end

  private

  def validate_headers!(header)
    required_headers = ['Nombre']
    missing = required_headers - header

    if missing.any?
      raise ValidationError, "Columnas obligatorias faltantes: #{missing.join(', ')}"
    end
  end

  def validate_row!(row, row_number)
    # Solo validar que el nombre esté presente
    if row['Nombre'].blank?
      raise ValidationError, "Fila #{row_number}: El nombre es obligatorio"
    end
  end

  def normalize_row(row)
    row.transform_values do |value|
      # Convertir strings vacíos y 'nan' a nil
      value = nil if value.to_s.strip.empty? || value.to_s.downcase == 'nan'
      value
    end
  end
end
'@
    Set-Content -Path $servicePath -Value $serviceContent
    Write-Success "Creado: $servicePath"
} else {
    Write-Warning "OMITIDO: $servicePath ya existe (no se modificó)"
}

# Crear migración (con timestamp único)
Write-Info "Paso 6: Creando migración para actualizar constraints..."
$migrationTimestamp = Get-Date -Format "yyyyMMddHHmmss"
$migrationPath = "db/migrate/${migrationTimestamp}_update_enfermeras_constraints.rb"
$migrationContent = @'
# frozen_string_literal: true

class UpdateEnfermerasConstraints < ActiveRecord::Migration[7.0]
  def change
    # IMPORTANTE: Revisa esta migración antes de ejecutarla
    # Ajusta según la estructura real de tu tabla enfermeras

    # Eliminar índice UNIQUE del DNI si existe (descomenta si aplica)
    # remove_index :enfermeras, :dni if index_exists?(:enfermeras, :dni)

    # Agregar índice compuesto: UNIQUE por workspace_id + dni
    # add_index :enfermeras, [:workspace_id, :dni], unique: true, 
    #           name: 'index_enfermeras_on_workspace_and_dni'

    # Permitir que DNI, email y teléfono sean NULL (descomenta si aplica)
    # change_column_null :enfermeras, :dni, true
    # change_column_null :enfermeras, :email, true
    # change_column_null :enfermeras, :telefono, true

    # Asegurar que nombre NO sea NULL (descomenta si aplica)
    # change_column_null :enfermeras, :nombre, false
  end
end
'@
Set-Content -Path $migrationPath -Value $migrationContent
Write-Success "Creado: $migrationPath"
Write-Warning "IMPORTANTE: Revisa y descomenta las líneas necesarias en la migración antes de ejecutarla"

# Crear template de modelo Enfermera actualizado
Write-Info "Paso 7: Creando template de modelo Enfermera..."
$modelTemplatePath = "app/models/enfermera_TEMPLATE.rb"
$modelTemplateContent = @'
# frozen_string_literal: true

# TEMPLATE: Revisa y adapta este código para tu modelo Enfermera actual
# NO BORRES tu modelo original, copia las partes que necesites

class Enfermera < ApplicationRecord
  # Relación con workspace (descomenta si aplica)
  # belongs_to :workspace

  # O usa el concern (descomenta si aplica)
  # include WorkspaceScoped

  # Validaciones
  validates :nombre, presence: true

  # DNI, email y teléfono únicos SOLO dentro del workspace (si tienen valor)
  # Descomenta estas líneas si tu tabla tiene workspace_id
  # validates :dni, uniqueness: { scope: :workspace_id, allow_blank: true }
  # validates :email, uniqueness: { scope: :workspace_id, allow_blank: true }

  # Para validar formato de email solo si está presente
  validates :email, format: { with: URI::MailTo::EMAIL_REGEXP, allow_blank: true }, 
            if: -> { email.present? }
end
'@
Set-Content -Path $modelTemplatePath -Value $modelTemplateContent
Write-Success "Creado: $modelTemplatePath (revisa y adapta a tu modelo)"

# Crear archivo de instrucciones
Write-Info "Paso 8: Creando archivo de instrucciones..."
$instructionsPath = "INSTRUCCIONES_ACTUALIZACION.md"
$instructionsContent = @'
# Instrucciones para Actualizar la Aplicación

## Archivos Creados

Este script ha creado los siguientes archivos nuevos:

1. `app/models/current.rb` - Modelo para contexto de workspace
2. `app/models/concerns/workspace_scoped.rb` - Concern para multi-tenancy
3. `app/services/enfermera_import_service.rb` - Servicio de importación
4. `db/migrate/XXXXXX_update_enfermeras_constraints.rb` - Migración
5. `app/models/enfermera_TEMPLATE.rb` - Template del modelo

## Pasos a Seguir (ORDEN IMPORTANTE)

### 1. Revisa tu Esquema Actual
```bash
# Ver estructura de la tabla enfermeras
rails db
.schema enfermeras
.exit
```

### 2. Ajusta la Migración
- Abre `db/migrate/XXXXXX_update_enfermeras_constraints.rb`
- Descomenta las líneas que apliquen a tu caso
- Verifica que los nombres de columnas coincidan

### 3. Actualiza el Modelo Enfermera
- Abre `app/models/enfermera.rb` (tu modelo actual)
- Revisa `app/models/enfermera_TEMPLATE.rb`
- Copia las validaciones que necesites

### 4. Actualiza el Controller
Si tienes un controller de importación, actualízalo para usar el servicio:
```ruby
def import
  file = params[:file]
  workspace = current_user.workspace # Ajusta según tu lógica
  
  service = EnfermeraImportService.new(file, workspace)
  result = service.call
  
  flash[:notice] = "Importadas #{result[:created]} enfermeras"
rescue EnfermeraImportService::ValidationError => e
  flash[:alert] = e.message
end
```

### 5. Ejecuta las Migraciones (con precaución)
```bash
# Primero prueba en consola
rails db:migrate:status

# Ejecuta la migración
rails db:migrate

# Si algo sale mal, puedes revertir:
rails db:rollback
```

### 6. Prueba la Importación
- Prueba primero con un archivo pequeño
- Verifica que los errores se muestren correctamente

## Rollback si Algo Sale Mal

Si necesitas revertir los cambios:

```bash
# Revertir migración
rails db:rollback

# Restaurar backup de BD
copy backups\TIMESTAMP\development.sqlite3.backup db\development.sqlite3
```

## Notas Importantes

- El script NO modificó archivos existentes
- Revisa cada archivo antes de usarlo
- Adapta el código a tu estructura actual
- Prueba en desarrollo antes de producción
'@
Set-Content -Path $instructionsPath -Value $instructionsContent
Write-Success "Creado: $instructionsPath"

# Resumen final
Write-Info ""
Write-Info "=== RESUMEN ==="
Write-Success "✓ Backup creado en: $backupDir"
Write-Success "✓ Archivos nuevos creados (NO se modificaron existentes)"
Write-Warning "⚠ Siguiente paso: Lee $instructionsPath"
Write-Warning "⚠ IMPORTANTE: Revisa la migración antes de ejecutarla"
Write-Info ""
Write-Info "Para continuar:"
Write-Info "  1. Abre $instructionsPath"
Write-Info "  2. Revisa db/migrate/${migrationTimestamp}_update_enfermeras_constraints.rb"
Write-Info "  3. Ajusta según tu estructura de base de datos"
Write-Info "  4. Ejecuta: rails db:migrate"
Write-Info ""
Write-Success "Script completado exitosamente"
"""

# Guardar el script
with open('update_enfermeras_app.ps1', 'w', encoding='utf-8-sig') as f:
    f.write(ps1_script)

print("✓ Script PowerShell generado: update_enfermeras_app.ps1")
print("\nPara ejecutar el script:")
print("1. Abre PowerShell como Administrador")
print("2. Navega a la raíz de tu proyecto Rails")
print("3. Ejecuta: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass")
print("4. Ejecuta: .\\update_enfermeras_app.ps1")
