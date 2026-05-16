#!/bin/bash

# Script de Validación Rápida - Asignación Manual de Pedidos
# Ruta Fácil - 16 de Mayo de 2026

set -e

echo "================================================================================"
echo "VALIDACIÓN RÁPIDA - ASIGNACIÓN MANUAL DE PEDIDOS"
echo "================================================================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir resultado
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        exit 1
    fi
}

# ============================================================================
echo "PASO 1: Validación del Backend"
echo "============================================================================"
echo ""

cd backend

echo "  1.1 Ejecutando: python manage.py check"
python manage.py check
check "Backend check completado"

echo ""
echo "  1.2 Buscando archivo serializers.py modificado"
grep -q "AssignPedidoRequestSerializer" logistics/serializers.py
check "AssignPedidoRequestSerializer encontrado"

grep -q "RepartidorInfoSerializer" logistics/serializers.py
check "RepartidorInfoSerializer encontrado"

grep -q "PedidoDetailResponseSerializer" logistics/serializers.py
check "PedidoDetailResponseSerializer encontrado"

echo ""
echo "  1.3 Buscando endpoint en views.py"
grep -q "def assign" logistics/views.py
check "Método assign() encontrado"

grep -q "url_path='assign'" logistics/views.py
check "Ruta 'assign' configurada"

echo ""
echo "✓ Backend validado exitosamente"
echo ""

# ============================================================================
cd ../frontend

echo "PASO 2: Validación del Frontend"
echo "============================================================================"
echo ""

echo "  2.1 Buscando archivo api.js modificado"
grep -q "assignOrderManually" src/services/api.js
check "assignOrderManually() encontrada en api.js"

echo ""
echo "  2.2 Buscando archivo AppContext.jsx modificado"
grep -q "assignOrder" src/context/AppContext.jsx
check "assignOrder() encontrada en AppContext.jsx"

echo ""
echo "  2.3 Buscando componente ManualAssignModal.jsx"
[ -f "src/components/ManualAssignModal.jsx" ]
check "ManualAssignModal.jsx creado"

echo ""
echo "  2.4 Buscando estilos ManualAssignModal.css"
[ -f "src/components/ManualAssignModal.css" ]
check "ManualAssignModal.css creado"

echo ""
echo "  2.5 Buscando AdminDashboard actualizado"
grep -q "import { ManualAssignModal }" src/pages/admin/AdminDashboard.jsx
check "ManualAssignModal importado en AdminDashboard"

grep -q "handleOpenManualAssign" src/pages/admin/AdminDashboard.jsx
check "handleOpenManualAssign() encontrado"

grep -q "handleConfirmManualAssign" src/pages/admin/AdminDashboard.jsx
check "handleConfirmManualAssign() encontrado"

grep -q "Pedidos pendientes" src/pages/admin/AdminDashboard.jsx
check "Sección 'Pedidos pendientes' encontrada"

echo ""
echo "✓ Frontend validado exitosamente"
echo ""

# ============================================================================
cd ..

echo "PASO 3: Validación de Documentación"
echo "============================================================================"
echo ""

echo "  3.1 Buscando archivo de auditoría"
[ -f "AUDITORIA_ASIGNACION_MANUAL.md" ]
check "AUDITORIA_ASIGNACION_MANUAL.md creado"

echo ""
echo "  3.2 Buscando archivo de implementación"
[ -f "IMPLEMENTACION_ASIGNACION_MANUAL.md" ]
check "IMPLEMENTACION_ASIGNACION_MANUAL.md creado"

echo ""
echo "  3.3 Buscando resumen ejecutivo"
[ -f "RESUMEN_ASIGNACION_MANUAL.md" ]
check "RESUMEN_ASIGNACION_MANUAL.md creado"

echo ""
echo "  3.4 Buscando checklist final"
[ -f "CHECKLIST_ASIGNACION_MANUAL.md" ]
check "CHECKLIST_ASIGNACION_MANUAL.md creado"

echo ""
echo "✓ Documentación validada exitosamente"
echo ""

# ============================================================================
echo "================================================================================"
echo "✓ VALIDACIÓN COMPLETADA EXITOSAMENTE"
echo "================================================================================"
echo ""
echo "Próximos pasos:"
echo "1. cd backend && python manage.py test"
echo "2. cd frontend && npm run build"
echo "3. Probar manualmente desde http://127.0.0.1:5173"
echo "4. Ver AdminDashboard → sección 'Pedidos pendientes'"
echo ""
