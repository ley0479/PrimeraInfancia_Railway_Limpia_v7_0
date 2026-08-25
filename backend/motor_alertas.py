"""
Motor de alertas avanzado para SinergiaInfancia
"""
from modules.dbapi_compat import sqlite3
from datetime import datetime, timedelta
import json

from modules.seguridad.tenant_context import current_tenant_id

from models import (
    AlertaNivel, AlertaConfiguracion, EstadoUsuario, 
    EstadoNutricion, TipoGestante
)


class MotorAlertas:
    """Gestiona y genera alertas automáticas del sistema"""
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_db_connection(self):
        """Obtiene conexión a BD"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def limpiar_alertas_resueltas(self, dias=30):
        """Limpia alertas resueltas hace más de X días"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        fecha_limite = (datetime.now() - timedelta(days=dias)).isoformat()
        cursor.execute("""
            DELETE FROM alertas
            WHERE resuelta = 1 AND fecha_resolucion < ?
        """, (fecha_limite,))
        
        conn.commit()
        conn.close()
    
    # ==================== ALERTAS DE EDAD ====================
    def generar_alertas_edad(self):
        """Genera alertas por proximidad a edad de retiro"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        fid = int(current_tenant_id(1) or 1)
        # La alerta se identifica por documento; el id de master_ninos no es FK
        # de beneficiarios y nunca debe guardarse como si lo fuera.
        cursor.execute("""
            SELECT documento, nombre_completo AS nombres,
                   unidad_servicio AS unidad, fecha_nacimiento
            FROM master_ninos
            WHERE activo=1 AND COALESCE(fundacion_id,1)=?
        """, (fid,))
        
        beneficiarios = cursor.fetchall()
        alertas_creadas = 0
        
        for benef in beneficiarios:
            # Calcular edad
            edad_meses = self._calcular_edad_meses(benef['fecha_nacimiento'])
            
            # Verificar si ya existe alerta abierta para este beneficiario
            cursor.execute("""
                SELECT id FROM alertas
                WHERE tipo_alerta LIKE 'EDAD_%' AND detalles LIKE ? AND resuelta = 0
            """, (f'%{benef["documento"]}%',))
            
            alerta_existente = cursor.fetchone()
            
            nivel = None
            descripcion = None
            
            if edad_meses >= 71:
                nivel = AlertaNivel.CRITICA
                descripcion = f"CRÍTICO: {benef['nombres']} ({edad_meses} meses) cumplió edad de retiro"
            elif edad_meses >= 68:
                nivel = AlertaNivel.ROJO
                descripcion = f"ALERTA: {benef['nombres']} próximo a edad de retiro ({edad_meses} meses)"
            
            if nivel and not alerta_existente:
                cursor.execute("""
                    INSERT INTO alertas
                    (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                    VALUES (?, ?, ?, ?, ?)
                """, ('EDAD_RETIRO', nivel, descripcion,
                      json.dumps({
                          'documento': benef['documento'],
                          'edad_meses': edad_meses,
                          'unidad': benef['unidad']
                      }), datetime.now().isoformat()))
                
                alertas_creadas += 1
        
        conn.commit()
        conn.close()
        
        return alertas_creadas
    
    # ==================== ALERTAS DE NUTRICIÓN ====================
    def generar_alertas_nutricion(self):
        """Genera alertas por controles vencidos o estado nutricional crítico"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        alertas_creadas = 0
        
        # 1. Controles vencidos
        fecha_vencimiento = (datetime.now() - timedelta(days=AlertaConfiguracion.DIAS_CONTROL_NUTRICION)).isoformat()
        
        fid = int(current_tenant_id(1) or 1)
        cursor.execute("""
            SELECT b.nombre_completo AS nombres, b.documento,
                   b.unidad_servicio AS unidad
            FROM master_ninos b
            LEFT JOIN master_salud_nutricion s
              ON s.version_id=b.version_id AND s.documento=b.documento
             AND s.activo=1 AND COALESCE(s.fundacion_id,1)=?
            WHERE b.activo=1 AND COALESCE(b.fundacion_id,1)=?
            GROUP BY b.documento,b.nombre_completo,b.unidad_servicio
            HAVING MAX(s.fecha_toma) IS NULL OR MAX(s.fecha_toma) < ?
        """, (fid, fid, fecha_vencimiento))
        
        vencidos = cursor.fetchall()
        
        for benef in vencidos:
            # Verificar si ya existe alerta abierta
            cursor.execute("""
                SELECT id FROM alertas
                WHERE tipo_alerta = 'NUTRICION_VENCIDA' AND detalles LIKE ? AND resuelta = 0
            """, (f'%{benef["documento"]}%',))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO alertas
                    (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                    VALUES (?, ?, ?, ?, ?)
                """, ('NUTRICION_VENCIDA', AlertaNivel.AMARILLO,
                      f"Control nutricional vencido: {benef['nombres']}",
                      json.dumps({
                          'documento': benef['documento'],
                          'unidad': benef['unidad']
                      }), datetime.now().isoformat()))
                
                alertas_creadas += 1
        
        # 2. Estados nutricionales críticos
        cursor.execute("""
            SELECT b.nombre_completo AS nombres,b.documento,
                   b.unidad_servicio AS unidad,s.estado_nutricional
            FROM master_ninos b JOIN master_salud_nutricion s
              ON s.version_id=b.version_id AND s.documento=b.documento
             AND s.activo=1 AND COALESCE(s.fundacion_id,1)=?
            WHERE b.activo=1 AND COALESCE(b.fundacion_id,1)=?
              AND s.estado_nutricional IN (?,?)
        """, (fid, fid, EstadoNutricion.DESNUTRICION, EstadoNutricion.RIESGO))
        
        criticos = cursor.fetchall()
        
        for benef in criticos:
            nivel = AlertaNivel.CRITICA if benef['estado_nutricional'] == EstadoNutricion.DESNUTRICION else AlertaNivel.ROJO
            
            # Verificar si ya existe alerta
            cursor.execute("""
                SELECT id FROM alertas
                WHERE tipo_alerta = 'NUTRICION_CRITICA' AND detalles LIKE ? AND resuelta = 0
            """, (f'%{benef["documento"]}%',))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO alertas
                    (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                    VALUES (?, ?, ?, ?, ?)
                """, ('NUTRICION_CRITICA', nivel,
                      f"Estado nutricional crítico: {benef['nombres']} - {benef['estado_nutricional']}",
                      json.dumps({
                          'documento': benef['documento'],
                          'unidad': benef['unidad'],
                          'estado': benef['estado_nutricional']
                      }), datetime.now().isoformat()))
                
                alertas_creadas += 1
        
        conn.commit()
        conn.close()
        
        return alertas_creadas
    
    # ==================== ALERTAS DE COBERTURA ====================
    def generar_alertas_cobertura(self):
        """Genera alertas por vacantes en unidades"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        alertas_creadas = 0
        
        # Obtener conteo por unidad
        cursor.execute("""
            SELECT unidad_servicio AS unidad, COUNT(*) as total
            FROM master_ninos
            WHERE activo=1 AND COALESCE(fundacion_id,1)=?
            GROUP BY unidad_servicio
        """, (int(current_tenant_id(1) or 1),))
        
        unidades = cursor.fetchall()
        
        for unidad in unidades:
            vacantes = AlertaConfiguracion.COBERTURA_MINIMA - unidad['total']
            
            if vacantes > 0:
                # Verificar si ya existe alerta abierta
                cursor.execute("""
                    SELECT id FROM alertas
                    WHERE tipo_alerta = 'COBERTURA_BAJA' 
                    AND detalles LIKE ? AND resuelta = 0
                """, (f'%"{unidad["unidad"]}"%',))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO alertas
                        (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                        VALUES (?, ?, ?, ?, ?)
                    """, ('COBERTURA_BAJA', AlertaNivel.AMARILLO,
                          f"Unidad {unidad['unidad']}: {vacantes} vacantes disponibles",
                          json.dumps({
                              'unidad': unidad['unidad'],
                              'usuarios_actuales': unidad['total'],
                              'vacantes': vacantes
                          }), datetime.now().isoformat()))
                    
                    alertas_creadas += 1
        
        conn.commit()
        conn.close()
        
        return alertas_creadas
    
    # ==================== ALERTAS DE GESTANTES ====================
    def generar_alertas_gestantes(self):
        """Genera alertas para gestantes próximas al parto o lactantes pendientes"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        alertas_creadas = 0
        
        # Gestantes próximas al parto (últimas 2 semanas)
        cursor.execute("""
            SELECT id, nombres, documento, unidad, fecha_probable_parto
            FROM gestantes
            WHERE estado = ? AND tipo_gestante = ?
            AND julianday(fecha_probable_parto) - julianday('now') <= ?
            AND julianday(fecha_probable_parto) - julianday('now') > 0
        """, (EstadoUsuario.ACTIVO, TipoGestante.EMBARAZADA, 
              AlertaConfiguracion.SEMANAS_ALERTA_PARTO * 7))
        
        proximas_parto = cursor.fetchall()
        
        for gestante in proximas_parto:
            cursor.execute("""
                SELECT id FROM alertas
                WHERE tipo_alerta = 'GESTANTE_PROXIMO_PARTO' 
                AND detalles LIKE ? AND resuelta = 0
            """, (f'%{gestante["documento"]}%',))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO alertas
                    (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                    VALUES (?, ?, ?, ?, ?)
                """, ('GESTANTE_PROXIMO_PARTO', AlertaNivel.ROJO,
                      f"GESTANTE PRÓXIMA AL PARTO: {gestante['nombres']}",
                      json.dumps({
                          'documento': gestante['documento'],
                          'unidad': gestante['unidad'],
                          'fecha_probable': gestante['fecha_probable_parto']
                      }), datetime.now().isoformat()))
                
                alertas_creadas += 1
        
        # Lactantes con cambio pendiente (pasaron fecha de parto hace 10 días)
        cursor.execute("""
            SELECT id, nombres, documento, unidad, fecha_nacimiento_bebe
            FROM gestantes
            WHERE estado = ? AND tipo_gestante = ?
            AND julianday('now') - julianday(fecha_nacimiento_bebe) >= 1
            AND julianday('now') - julianday(fecha_nacimiento_bebe) < 10
        """, (EstadoUsuario.ACTIVO, TipoGestante.EMBARAZADA))
        
        para_cambiar = cursor.fetchall()
        
        for gestante in para_cambiar:
            cursor.execute("""
                SELECT id FROM alertas
                WHERE tipo_alerta = 'TRANSICION_LACTANTE_PENDIENTE'
                AND detalles LIKE ? AND resuelta = 0
            """, (f'%{gestante["documento"]}%',))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO alertas
                    (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                    VALUES (?, ?, ?, ?, ?)
                """, ('TRANSICION_LACTANTE_PENDIENTE', AlertaNivel.AMARILLO,
                      f"CAMBIO A LACTANTE: {gestante['nombres']}",
                      json.dumps({
                          'documento': gestante['documento'],
                          'unidad': gestante['unidad']
                      }), datetime.now().isoformat()))
                
                alertas_creadas += 1
        
        conn.commit()
        conn.close()
        
        return alertas_creadas
    
    # ==================== ALERTAS DE DUPLICADOS ====================
    def generar_alertas_duplicados(self):
        """Detecta usuarios potencialmente duplicados"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        alertas_creadas = 0
        
        # Mismo documento en múltiples unidades
        cursor.execute("""
            SELECT documento, COUNT(*) as cantidad, 
                   GROUP_CONCAT(unidad_servicio, ', ') as unidades,
                   GROUP_CONCAT(id, ',') as ids
            FROM master_ninos
            WHERE activo=1 AND COALESCE(fundacion_id,1)=?
              AND documento IS NOT NULL AND documento != ''
            GROUP BY documento
            HAVING COUNT(*) > 1
        """, (int(current_tenant_id(1) or 1),))
        
        duplicados_doc = cursor.fetchall()
        
        for duplicado in duplicados_doc:
            cursor.execute("""
                SELECT id FROM alertas
                WHERE tipo_alerta = 'USUARIO_DUPLICADO'
                AND detalles LIKE ? AND resuelta = 0
            """, (f'%{duplicado["documento"]}%',))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO alertas
                    (tipo_alerta, nivel, descripcion, detalles, fecha_generacion)
                    VALUES (?, ?, ?, ?, ?)
                """, ('USUARIO_DUPLICADO', AlertaNivel.ROJO,
                      f"USUARIO DUPLICADO: Documento {duplicado['documento']} en {duplicado['cantidad']} registros",
                      json.dumps({
                          'documento': duplicado['documento'],
                          'cantidad': duplicado['cantidad'],
                          'unidades': duplicado['unidades'].split(', ')
                      }), datetime.now().isoformat()))
                
                alertas_creadas += 1
        
        conn.commit()
        conn.close()
        
        return alertas_creadas
    
    # ==================== GENERADOR MASIVO DE ALERTAS ====================
    def generar_todas_alertas(self):
        """Ejecuta generación de todas las alertas"""
        print("[MOTOR DE ALERTAS] Iniciando generación masiva...")
        
        self.limpiar_alertas_resueltas()
        
        resultados = {
            'edad': self.generar_alertas_edad(),
            'nutricion': self.generar_alertas_nutricion(),
            'cobertura': self.generar_alertas_cobertura(),
            'gestantes': self.generar_alertas_gestantes(),
            'duplicados': self.generar_alertas_duplicados()
        }
        
        total = sum(resultados.values())
        print(f"[MOTOR DE ALERTAS] Alertas generadas: {total}")
        
        return resultados
    
    @staticmethod
    def _calcular_edad_meses(fecha_nacimiento):
        """Calcula edad en meses"""
        try:
            if isinstance(fecha_nacimiento, str):
                nac = datetime.fromisoformat(fecha_nacimiento.replace('Z', '+00:00'))
            else:
                nac = fecha_nacimiento
            
            hoy = datetime.now()
            meses = (hoy.year - nac.year) * 12 + (hoy.month - nac.month)
            return max(0, meses)
        except Exception:
            return 0
