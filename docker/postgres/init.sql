-- ============================================
-- Script de Inicialización PostgreSQL
-- Planificador de Turnos de Enfermería
-- ============================================

-- Mensaje inicial
DO $$
BEGIN
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'Inicializando Base de Datos: Planificador Turnos';
    RAISE NOTICE '=================================================';
END $$;

-- ============================================
-- EXTENSIONES
-- ============================================

-- UUID para generar identificadores únicos
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
COMMENT ON EXTENSION "uuid-ossp" IS 'Generación de UUIDs';

-- pg_trgm para búsquedas de similitud y texto completo
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
COMMENT ON EXTENSION "pg_trgm" IS 'Búsqueda de similitud de texto con trigramas';

-- unaccent para normalizar búsquedas sin acentos
CREATE EXTENSION IF NOT EXISTS "unaccent";
COMMENT ON EXTENSION "unaccent" IS 'Eliminación de acentos para búsquedas';

-- hstore para almacenamiento clave-valor (opcional)
CREATE EXTENSION IF NOT EXISTS "hstore";
COMMENT ON EXTENSION "hstore" IS 'Almacenamiento de pares clave-valor';

-- btree_gin para índices GIN en tipos de datos estándar
CREATE EXTENSION IF NOT EXISTS "btree_gin";
COMMENT ON EXTENSION "btree_gin" IS 'Índices GIN para tipos de datos B-tree';

-- pgcrypto para funciones criptográficas
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
COMMENT ON EXTENSION "pgcrypto" IS 'Funciones criptográficas';

-- ============================================
-- CONFIGURACIÓN DE BÚSQUEDA DE TEXTO COMPLETO
-- ============================================

-- Crear configuración de búsqueda en español
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS spanish_unaccent (COPY = spanish);

-- Alterar el diccionario para usar unaccent
ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH unaccent, spanish_stem;

COMMENT ON TEXT SEARCH CONFIGURATION spanish_unaccent IS 'Configuración de búsqueda de texto en español sin acentos';

-- ============================================
-- FUNCIONES ÚTILES
-- ============================================

-- Función para actualizar timestamp automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Actualiza automáticamente el campo updated_at';

-- Función para generar slug desde texto
CREATE OR REPLACE FUNCTION generate_slug(text_input TEXT)
RETURNS TEXT AS $$
DECLARE
    slug TEXT;
BEGIN
    slug := lower(unaccent(text_input));
    slug := regexp_replace(slug, '[^a-z0-9\s-]', '', 'gi');
    slug := regexp_replace(slug, '\s+', '-', 'g');
    slug := regexp_replace(slug, '-+', '-', 'g');
    slug := trim(both '-' from slug);
    RETURN slug;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_slug(TEXT) IS 'Genera un slug URL-friendly desde texto';

-- Función para búsqueda fuzzy de enfermeras
CREATE OR REPLACE FUNCTION search_enfermeras(search_term TEXT)
RETURNS TABLE(
    id INTEGER,
    nombre VARCHAR,
    email VARCHAR,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.nombre,
        e.email,
        GREATEST(
            similarity(e.nombre, search_term),
            similarity(e.email, search_term)
        ) as similarity_score
    FROM turnos_enfermera e
    WHERE
        e.nombre % search_term
        OR e.email % search_term
        OR e.nombre ILIKE '%' || search_term || '%'
        OR e.email ILIKE '%' || search_term || '%'
    ORDER BY similarity_score DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_enfermeras(TEXT) IS 'Búsqueda fuzzy de enfermeras por nombre o email';

-- Función para limpiar ejecuciones antiguas
CREATE OR REPLACE FUNCTION cleanup_old_executions(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM turnos_ejecucionplanificacion
    WHERE
        fecha_inicio < CURRENT_DATE - (days_old || ' days')::INTERVAL
        AND estado IN ('COMPLETADA', 'ERROR', 'CANCELADA');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Eliminadas % ejecuciones antiguas (> % días)', deleted_count, days_old;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_executions(INTEGER) IS 'Limpia ejecuciones antiguas de la base de datos';

-- Función para calcular estadísticas de configuración
CREATE OR REPLACE FUNCTION config_statistics(config_id INTEGER)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_ejecuciones', COUNT(*),
        'completadas', COUNT(*) FILTER (WHERE estado = 'COMPLETADA'),
        'fallidas', COUNT(*) FILTER (WHERE estado = 'ERROR'),
        'penalizacion_promedio', AVG(penalizacion_total) FILTER (WHERE estado = 'COMPLETADA'),
        'duracion_promedio', AVG(duracion) FILTER (WHERE estado = 'COMPLETADA'),
        'ultima_ejecucion', MAX(fecha_inicio)
    )
    INTO result
    FROM turnos_ejecucionplanificacion
    WHERE configuracion_id = config_id;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION config_statistics(INTEGER) IS 'Retorna estadísticas JSON de una configuración';

-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Vista de enfermeras activas con estadísticas
CREATE OR REPLACE VIEW v_enfermeras_activas AS
SELECT
    e.id,
    e.nombre,
    e.email,
    e.activa,
    e.fecha_alta,
    COUNT(DISTINCT ep.id) as total_planificaciones,
    MAX(ep.fecha_inicio) as ultima_planificacion
FROM turnos_enfermera e
LEFT JOIN turnos_configuracionplanificacion_enfermeras ce ON e.id = ce.enfermera_id
LEFT JOIN turnos_ejecucionplanificacion ep ON ce.configuracionplanificacion_id = ep.configuracion_id
WHERE e.activa = true
GROUP BY e.id, e.nombre, e.email, e.activa, e.fecha_alta;

COMMENT ON VIEW v_enfermeras_activas IS 'Vista de enfermeras activas con estadísticas de uso';

-- Vista de configuraciones con estadísticas
CREATE OR REPLACE VIEW v_configuraciones_stats AS
SELECT
    c.id,
    c.nombre,
    c.descripcion,
    c.num_dias,
    c.activa,
    c.fecha_creacion,
    COUNT(DISTINCT e.id) as num_ejecuciones,
    COUNT(DISTINCT e.id) FILTER (WHERE e.estado = 'COMPLETADA') as ejecuciones_exitosas,
    AVG(e.penalizacion_total) FILTER (WHERE e.estado = 'COMPLETADA') as penalizacion_promedio,
    AVG(e.duracion) FILTER (WHERE e.estado = 'COMPLETADA') as duracion_promedio_segundos,
    MAX(e.fecha_inicio) as ultima_ejecucion
FROM turnos_configuracionplanificacion c
LEFT JOIN turnos_ejecucionplanificacion e ON c.id = e.configuracion_id
GROUP BY c.id, c.nombre, c.descripcion, c.num_dias, c.activa, c.fecha_creacion;

COMMENT ON VIEW v_configuraciones_stats IS 'Vista de configuraciones con estadísticas agregadas';

-- Vista de ejecuciones con información completa
CREATE OR REPLACE VIEW v_ejecuciones_completas AS
SELECT
    e.id,
    e.estado,
    e.fecha_inicio,
    e.fecha_fin,
    e.duracion,
    e.penalizacion_total,
    e.es_optima,
    c.nombre as configuracion_nombre,
    c.num_dias,
    u.username as usuario,
    u.email as usuario_email,
    (SELECT COUNT(*) FROM jsonb_object_keys(e.planilla)) as dias_planificados
FROM turnos_ejecucionplanificacion e
JOIN turnos_configuracionplanificacion c ON e.configuracion_id = c.id
JOIN turnos_usuario u ON e.usuario_id = u.id;

COMMENT ON VIEW v_ejecuciones_completas IS 'Vista de ejecuciones con información de configuración y usuario';

-- ============================================
-- ÍNDICES ADICIONALES PARA OPTIMIZACIÓN
-- ============================================

-- Nota: Django crea muchos índices automáticamente,
-- estos son adicionales para mejorar el rendimiento

-- Índices para búsqueda de texto completo
DO $$
BEGIN
    -- Solo crear si la tabla existe (Django la creará después)
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'turnos_enfermera') THEN
        CREATE INDEX IF NOT EXISTS idx_enfermera_nombre_trgm
        ON turnos_enfermera USING gin (nombre gin_trgm_ops);

        CREATE INDEX IF NOT EXISTS idx_enfermera_email_trgm
        ON turnos_enfermera USING gin (email gin_trgm_ops);
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'turnos_configuracionplanificacion') THEN
        CREATE INDEX IF NOT EXISTS idx_configuracion_nombre_trgm
        ON turnos_configuracionplanificacion USING gin (nombre gin_trgm_ops);
    END IF;
END $$;

-- ============================================
-- CONFIGURACIÓN DE PARÁMETROS
-- ============================================

-- Configurar parámetros de búsqueda
ALTER DATABASE planificador_turnos SET default_text_search_config = 'spanish_unaccent';

-- Configurar timezone
ALTER DATABASE planificador_turnos SET timezone = 'Europe/Madrid';

-- Optimización de búsquedas
ALTER DATABASE planificador_turnos SET pg_trgm.similarity_threshold = 0.3;

-- ============================================
-- POLÍTICAS DE SEGURIDAD (ROW LEVEL SECURITY)
-- ============================================

-- Nota: RLS se configurará después de que Django cree las tablas
-- Ejemplo de cómo se vería:
/*
ALTER TABLE turnos_configuracionplanificacion ENABLE ROW LEVEL SECURITY;

CREATE POLICY configuracion_isolation ON turnos_configuracionplanificacion
    USING (usuario_id = current_setting('app.current_user_id')::integer);
*/

-- ============================================
-- TRIGGER PARA AUDITORÍA AUTOMÁTICA
-- ============================================

-- Función genérica para auditoría
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO turnos_auditlog (
            usuario_id,
            accion,
            modelo,
            objeto_id,
            descripcion,
            metadatos,
            timestamp
        ) VALUES (
            COALESCE(current_setting('app.current_user_id', true)::integer, NULL),
            'CREATE',
            TG_TABLE_NAME,
            NEW.id,
            'Registro creado',
            row_to_json(NEW)::jsonb,
            CURRENT_TIMESTAMP
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO turnos_auditlog (
            usuario_id,
            accion,
            modelo,
            objeto_id,
            descripcion,
            metadatos,
            timestamp
        ) VALUES (
            COALESCE(current_setting('app.current_user_id', true)::integer, NULL),
            'UPDATE',
            TG_TABLE_NAME,
            NEW.id,
            'Registro actualizado',
            jsonb_build_object('old', row_to_json(OLD)::jsonb, 'new', row_to_json(NEW)::jsonb),
            CURRENT_TIMESTAMP
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO turnos_auditlog (
            usuario_id,
            accion,
            modelo,
            objeto_id,
            descripcion,
            metadatos,
            timestamp
        ) VALUES (
            COALESCE(current_setting('app.current_user_id', true)::integer, NULL),
            'DELETE',
            TG_TABLE_NAME,
            OLD.id,
            'Registro eliminado',
            row_to_json(OLD)::jsonb,
            CURRENT_TIMESTAMP
        );
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION audit_trigger_function() IS 'Función genérica para auditoría automática de cambios';

-- ============================================
-- MANTENIMIENTO AUTOMÁTICO
-- ============================================

-- Función para reindexar tablas críticas
CREATE OR REPLACE FUNCTION reindex_critical_tables()
RETURNS TEXT AS $$
BEGIN
    REINDEX TABLE CONCURRENTLY turnos_enfermera;
    REINDEX TABLE CONCURRENTLY turnos_configuracionplanificacion;
    REINDEX TABLE CONCURRENTLY turnos_ejecucionplanificacion;
    REINDEX TABLE CONCURRENTLY turnos_usuario;

    RETURN 'Reindexación completada';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reindex_critical_tables() IS 'Reindexa las tablas más importantes';

-- Función para análisis de estadísticas
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS TEXT AS $$
BEGIN
    ANALYZE turnos_enfermera;
    ANALYZE turnos_configuracionplanificacion;
    ANALYZE turnos_ejecucionplanificacion;
    ANALYZE turnos_usuario;
    ANALYZE turnos_auditlog;

    RETURN 'Estadísticas actualizadas';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_table_statistics() IS 'Actualiza estadísticas de las tablas principales';

-- ============================================
-- VACUUM AUTOMÁTICO OPTIMIZADO
-- ============================================

ALTER TABLE IF EXISTS turnos_auditlog SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

ALTER TABLE IF EXISTS turnos_ejecucionplanificacion SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

-- ============================================
-- ROLES Y PERMISOS (Opcional)
-- ============================================

-- Crear rol de solo lectura
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly_pass';

        -- Otorgar permisos de solo lectura
        GRANT CONNECT ON DATABASE planificador_turnos TO readonly_user;
        GRANT USAGE ON SCHEMA public TO readonly_user;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

        -- Permisos futuros
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO readonly_user;
    END IF;
END $$;

-- ============================================
-- DATOS INICIALES (Seeds)
-- ============================================

-- Insertar tipos de turno por defecto (si no existen)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'turnos_tipoturno') THEN
        RAISE NOTICE 'Tabla turnos_tipoturno aún no existe. Django la creará.';
    ELSE
        -- Insertar turnos por defecto
        INSERT INTO turnos_tipoturno (nombre, hora_inicio, hora_fin, activo)
        VALUES
            ('MAÑANA', '07:00:00', '15:00:00', true),
            ('TARDE', '15:00:00', '23:00:00', true),
            ('NOCHE', '23:00:00', '07:00:00', true)
        ON CONFLICT DO NOTHING;

        RAISE NOTICE 'Tipos de turno insertados';
    END IF;
END $$;

-- ============================================
-- MONITOREO Y LOGGING
-- ============================================

-- Habilitar logging de queries lentas
ALTER DATABASE planificador_turnos SET log_min_duration_statement = 1000;
ALTER DATABASE planificador_turnos SET log_statement = 'mod';
ALTER DATABASE planificador_turnos SET log_duration = on;

-- ============================================
-- INFORMACIÓN DE VERSIÓN
-- ============================================

CREATE TABLE IF NOT EXISTS db_version (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO db_version (version, description)
VALUES ('1.0.0', 'Inicialización completa de base de datos')
ON CONFLICT (version) DO NOTHING;

-- ============================================
-- VERIFICACIÓN FINAL
-- ============================================

DO $$
DECLARE
    extension_count INTEGER;
    function_count INTEGER;
    view_count INTEGER;
BEGIN
    -- Contar extensiones
    SELECT COUNT(*) INTO extension_count
    FROM pg_extension
    WHERE extname IN ('uuid-ossp', 'pg_trgm', 'unaccent', 'hstore', 'pgcrypto');

    -- Contar funciones personalizadas
    SELECT COUNT(*) INTO function_count
    FROM pg_proc
    WHERE proname IN (
        'update_updated_at_column',
        'generate_slug',
        'search_enfermeras',
        'cleanup_old_executions',
        'config_statistics'
    );

    -- Contar vistas
    SELECT COUNT(*) INTO view_count
    FROM pg_views
    WHERE schemaname = 'public'
    AND viewname LIKE 'v_%';

    RAISE NOTICE '';
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'VERIFICACIÓN DE INICIALIZACIÓN:';
    RAISE NOTICE '  ✓ Extensiones instaladas: %', extension_count;
    RAISE NOTICE '  ✓ Funciones creadas: %', function_count;
    RAISE NOTICE '  ✓ Vistas creadas: %', view_count;
    RAISE NOTICE '  ✓ Base de datos: %', current_database();
    RAISE NOTICE '  ✓ Usuario: %', current_user;
    RAISE NOTICE '  ✓ Versión PostgreSQL: %', version();
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'Base de datos inicializada correctamente ✓';
    RAISE NOTICE '=================================================';
END $$;
