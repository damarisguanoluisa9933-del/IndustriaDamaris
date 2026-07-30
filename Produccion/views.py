from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum
from django.core.mail import send_mail
from django.conf import settings
import json

from .models import (
    LineaEnsamblaje, Maquinaria, Supervisor, 
    Operario, Insumo, OrdenFabricacion, 
    DetalleInsumoLote, RegistroInterrupcion
)

# ==========================================
# MÓDULOS DE AUTENTICACIÓN NATIVA
# ==========================================

def vista_login(request):
    # Si el usuario ya inicio sesion, lo mandamos directo a la pagina de inicio para que no vuelva a loguearse
    if request.user.is_authenticated:
        return redirect('inicio')
        
    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        clave_input = request.POST.get('password')

        # Intentamos entrar con el usuario normal de Django
        user = authenticate(request, username=usuario_input, password=clave_input)
        
        # Si no funciono, buscamos si metio la cedula de un supervisor para rescatar su usuario vinculado
        if user is None:
            try:
                sup = Supervisor.objects.get(cedula=usuario_input)
                if sup.usuario:
                    user = authenticate(request, username=sup.usuario.username, password=clave_input)
            except Supervisor.DoesNotExist:
                user = None

        # Si todo coincide, iniciamos la sesion y mostramos el mensaje de bienvenida
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenido al sistema, {user.first_name or user.username}.')
            return redirect('inicio')
        else:
            messages.error(request, 'Credenciales incorrectas. Verifique su usuario o contraseña.')

    return render(request, 'login.html')


def vista_registro(request):
    """Crea una cuenta nueva guardando el Usuario de Django y el Perfil de Supervisor al mismo tiempo."""
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        correo = request.POST.get('correo')
        username = request.POST.get('username')
        contrasena = request.POST.get('contrasena')
        foto = request.FILES.get('foto')

        # Validamos que no se repita el usuario ni la cedula
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya se encuentra registrado.')
            return render(request, 'registro.html')

        if Supervisor.objects.filter(cedula=cedula).exists():
            messages.error(request, 'La cédula ingresada ya está registrada en el sistema.')
            return render(request, 'registro.html')

        # 1. Creamos la cuenta base del sistema
        nuevo_user = User.objects.create_user(
            username=username,
            email=correo,
            password=contrasena,
            first_name=nombre,
            last_name=apellido
        )

        # 2. Creamos el perfil de supervisor amarrado a esa cuenta
        Supervisor.objects.create(
            usuario=nuevo_user,
            cedula=cedula,
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            foto=foto
        )

        messages.success(request, '¡Registro completado exitosamente! Ahora puede iniciar sesión.')
        return redirect('login')

    return render(request, 'registro.html')


def vista_logout(request):
    """Cierra la sesion actual del usuario."""
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')


# ==========================================
# VISTAS PRINCIPALES DEL SISTEMA
# ==========================================

@login_required(login_url='login')
def inicio(request):
    """Muestra la pantalla principal de bienvenida tras hacer login."""
    return render(request, "inicio.html")


@login_required(login_url='login')
def dashboard(request):
    """
    Arma las estadisticas y datos que se muestran en las graficas del panel de control.
    """
    # Sacamos las maquinas y sumamos las horas de uso de cada una
    maquinas_uso = (
        Maquinaria.objects.values('nombre')
        .annotate(total_horas=Sum('horas_uso'))
        .order_by('-total_horas')
    )
    # Nombres para los titulos del grafico
    etiquetas_maquinas = [item['nombre'] for item in maquinas_uso]
    
    # Convertimos las horas a float para que Chart.js en JS no de error al parsear decimales de Django
    datos_maquinas = [float(item['total_horas'] or 0) for item in maquinas_uso]

    # Si es el Administrador, le traemos todos los lotes de la planta
    if request.user.is_superuser:
        ordenes_qs = OrdenFabricacion.objects.all()
        detalles_qs = DetalleInsumoLote.objects.all()
    else:
        # getattr saca el perfil_supervisor de forma segura; si el usuario no tiene perfil devuelve None sin dar error
        supervisor = getattr(request.user, 'perfil_supervisor', None)
        
        # Si tiene perfil filtramos solo sus lotes; si no, devolvemos una lista vacia (none)
        ordenes_qs = OrdenFabricacion.objects.filter(supervisor=supervisor) if supervisor else OrdenFabricacion.objects.none()
        detalles_qs = DetalleInsumoLote.objects.filter(orden__supervisor=supervisor) if supervisor else DetalleInsumoLote.objects.none()

    # Agrupamos los lotes por estado (Pendiente, En Proceso, Finalizada) para el grafico de dona o pastel
    ordenes_estado = (
        ordenes_qs.values('estado')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    etiquetas_estado = [item['estado'] for item in ordenes_estado]
    datos_estado = [item['total'] for item in ordenes_estado]

    # Sumamos el total de desperdicio y materia prima gastada en la base de datos
    total_desperdicio = float(detalles_qs.aggregate(total=Sum('cantidad_desperdicio'))['total'] or 0)
    total_materia_usada = float(detalles_qs.aggregate(total=Sum('cantidad_utilizada'))['total'] or 0)

    # json.dumps convierte los arreglos de Python a texto tipo JSON para usarlos facil en JavaScript
    contexto = {
        'etiquetas_maquinas_json': json.dumps(etiquetas_maquinas),
        'datos_maquinas_json': json.dumps(datos_maquinas),
        'etiquetas_estado_json': json.dumps(etiquetas_estado),
        'datos_estado_json': json.dumps(datos_estado),
        'total_lotes': ordenes_qs.count(),
        'total_maquinas': Maquinaria.objects.count(),
        'total_operarios': Operario.objects.count(),
        'total_interrupciones': RegistroInterrupcion.objects.count(),
        'total_desperdicio': total_desperdicio,
        'total_materia_usada': total_materia_usada
    }

    return render(request, "dashboard.html", contexto)

# ==========================================
# FUNCIONALIDADES INTERACTIVAS (APIs AJAX)
# ==========================================

@login_required(login_url='login')
def api_lotes_fullcalendar(request):
    """Envia la lista de lotes en formato JSON para pintarlos en el calendario interactivo."""
    if request.user.is_superuser:
        ordenes = OrdenFabricacion.objects.all()
    else:
        supervisor = getattr(request.user, 'perfil_supervisor', None)
        ordenes = OrdenFabricacion.objects.filter(supervisor=supervisor) if supervisor else OrdenFabricacion.objects.none()

    eventos = []
    for o in ordenes:
        # Elegimos el color segun el estado del lote
        color = '#ffc107' if o.estado == 'Pendiente' else '#198754' if o.estado == 'En Proceso' else '#0d6efd'
        eventos.append({
            'id': o.id,
            'title': f"Lote {o.codigo_lote}: {o.producto}",
            'start': o.fecha_inicio_programada.isoformat(), # isoformat() da formato texto de fecha estandar
            'end': o.fecha_fin_programada.isoformat(),
            'backgroundColor': color,
            'borderColor': color
        })
    return JsonResponse(eventos, safe=False)


@csrf_exempt
@login_required(login_url='login')
def reordenar_cola_lotes(request):
    """Guarda el nuevo orden de prioridad cuando arrastras y sueltas un lote en la interfaz."""
    if request.method == 'POST':
        # Capturamos la lista de IDs ordenada que nos manda la vista en AJAX
        orden_ids = request.POST.getlist('orden_ids[]')
        for index, orden_id in enumerate(orden_ids, start=1):
            # Asignamos la nueva prioridad 1, 2, 3... segun el orden donde quedaron
            OrdenFabricacion.objects.filter(id=orden_id).update(prioridad_orden=index)
        return JsonResponse({'status': 'ok', 'message': 'Prioridad de lotes actualizada correctamente.'})
    return JsonResponse({'status': 'error'}, status=400)


@csrf_exempt
@login_required(login_url='login')
def cambiar_estado_maquina_hotkey(request):
    """Cambia el estado de una maquina rapido con teclado y si falla crea un reporte automatico."""
    if request.method == 'POST':
        maquina_id = request.POST.get('maquina_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        
        if not maquina_id or not nuevo_estado:
            return JsonResponse({'status': 'error', 'message': 'Faltan datos'}, status=400)

        # get_object_or_404 busca la maquina, si no existe lanza error 404 de Django sin colapsar el codigo
        maquina = get_object_or_404(Maquinaria, id=maquina_id)
        maquina.estado = nuevo_estado
        maquina.save()

        # Si la maquina se paro o fallo, registramos la interrupcion en la base de datos
        if nuevo_estado in ['Detenida', 'Falla']:
            RegistroInterrupcion.objects.create(
                maquina=maquina,
                motivo=f"Cambio rápido por teclado a {nuevo_estado}"
            )

        return JsonResponse({
            'status': 'ok', 
            'estado': maquina.estado,
            'id': maquina.id
        })
        
    return JsonResponse({'status': 'error'}, status=400)


@csrf_exempt
@login_required(login_url='login')
def aprobar_orden(request, id):
    """Finaliza un lote de produccion y le manda un correo al operario responsable."""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenFabricacion, id=id)
        orden.estado = 'Finalizada'
        
        # Si no pusieron cuanto se produjo, asumimos que se logro el 100% de lo programado
        if orden.cantidad_producida == 0:
            orden.cantidad_producida = orden.cantidad_programada
        orden.save()

        # Recalculamos los desperdicios ejecutando el save de cada insumo del lote
        for detalle in orden.detalles_insumos.all():
            detalle.save()

        try:
            data = json.loads(request.body) if request.body else {}
        except Exception:
            data = {}

        enviar_correo = data.get('enviar_correo', False)
        correo_enviado = False

        # Si seleccionaron la casilla de enviar correo y el operario tiene email registrado
        if enviar_correo:
            if orden.operario_encargado and orden.operario_encargado.correo:
                destino = orden.operario_encargado.correo
                asunto = f"Aprobación de Lote: {orden.codigo_lote} - Industria Damaris"
                mensaje = (
                    f"Estimado/a {orden.operario_encargado.nombres},\n\n"
                    f"La Orden de Fabricación para el Lote {orden.codigo_lote} ({orden.producto}) "
                    f"ha sido APROBADA Y FINALIZADA por el supervisor {orden.supervisor.nombre} {orden.supervisor.apellido}.\n\n"
                    f"Saludos cordiales,\nControl de Producción - Industria Damaris."
                )
                try:
                    send_mail(
                        asunto,
                        mensaje,
                        settings.DEFAULT_FROM_EMAIL,
                        [destino],
                        fail_silently=False,
                    )
                    correo_enviado = True
                except Exception as e:
                    correo_enviado = False

        msg = 'Se aprobó la orden y se finalizó correctamente.'
        return JsonResponse({'status': 'ok', 'correo_enviado': correo_enviado, 'mensaje': msg})

    return JsonResponse({'status': 'error'}, status=400)


# ==========================================
# CRUD ENTIDADES
# ==========================================

# LÍNEAS DE ENSAMBLAJE
@login_required(login_url='login')
def listado_lineas(request):
    """Muestra todas las lineas de ensamblaje en la tabla."""
    lineas = LineaEnsamblaje.objects.all()
    return render(request, 'LINEA_ENSAMBLAJE/listado_linea.html', {'lineas': lineas})



@login_required(login_url='login')
def nueva_linea(request):
    """Guarda una nueva línea generando un código secuencial automático (LIN-001) y validando duplicados."""
    if request.method == 'POST':
        nombre_linea = request.POST.get('nombre', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        
        # 1. Autogenerar el código secuencial si viene vacío o con el formato base 'LIN-'
        if not codigo or codigo == 'LIN-':
            ultimo_id = LineaEnsamblaje.objects.count() + 1
            codigo = f"LIN-{ultimo_id:03d}"
            while LineaEnsamblaje.objects.filter(codigo=codigo).exists():
                ultimo_id += 1
                codigo = f"LIN-{ultimo_id:03d}"

        # 2. Control estricto para evitar códigos duplicados en la base de datos
        if LineaEnsamblaje.objects.filter(codigo=codigo).exists():
            messages.error(request, f'El código de línea "{codigo}" ya está registrado en el sistema.')
            return render(request, 'LINEA_ENSAMBLAJE/nueva_linea.html', {'codigo_sugerido': codigo})

        # 3. Guardar en la base de datos
        LineaEnsamblaje.objects.create(
            nombre=nombre_linea,
            codigo=codigo,
            descripcion=request.POST.get('descripcion', '').strip(),
            foto=request.FILES.get('foto')
        )
        
        # 4. Mensaje de éxito limpio usando el nombre de la línea
        messages.success(request, f'Línea de ensamblaje "{nombre_linea}" registrada correctamente.')
        return redirect('listado_lineas')

    # Al cargar la página por primera vez, sugerimos el siguiente código libre (ej. LIN-001)
    ultimo_id = LineaEnsamblaje.objects.count() + 1
    codigo_sugerido = f"LIN-{ultimo_id:03d}"
    while LineaEnsamblaje.objects.filter(codigo=codigo_sugerido).exists():
        ultimo_id += 1
        codigo_sugerido = f"LIN-{ultimo_id:03d}"

    return render(request, 'LINEA_ENSAMBLAJE/nueva_linea.html', {'codigo_sugerido': codigo_sugerido})


@login_required(login_url='login')
def editar_linea(request, id):
    """Modifica una línea existente asegurando que el código no pertenezca a otra línea registrada."""
    linea = get_object_or_404(LineaEnsamblaje, id=id)
    
    if request.method == 'POST':
        nombre_linea = request.POST.get('nombre', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        
        # Validación de duplicados excluyendo el ID de la línea actual
        if LineaEnsamblaje.objects.filter(codigo=codigo).exclude(id=id).exists():
            messages.error(request, f'El código "{codigo}" ya está siendo utilizado por otra línea de ensamblaje.')
            return render(request, 'LINEA_ENSAMBLAJE/editar_linea.html', {'linea': linea})

        linea.nombre = nombre_linea
        linea.codigo = codigo
        linea.descripcion = request.POST.get('descripcion', '').strip()
        
        if request.FILES.get('foto'):
            linea.foto = request.FILES.get('foto')
            
        linea.save()
        messages.success(request, f'Línea "{nombre_linea}" actualizada correctamente.')
        return redirect('listado_lineas')

    return render(request, 'LINEA_ENSAMBLAJE/editar_linea.html', {'linea': linea})

@login_required(login_url='login')
def eliminar_linea(request, id):
    """Borra la linea de ensamblaje seleccionada."""
    get_object_or_404(LineaEnsamblaje, id=id).delete()
    messages.success(request, 'Línea eliminada correctamente.')
    return redirect('listado_lineas')


# MAQUINARIA
@login_required(login_url='login')
def listado_maquinarias(request):
    # select_related('linea') hace una sola consulta rápida trayendo los datos de la linea vinculada
    maquinarias = Maquinaria.objects.select_related('linea').all()
    return render(request, 'MAQUINARIA/listado_maquinaria.html', {'maquinarias': maquinarias})

@login_required(login_url='login')
def nueva_maquinaria(request):
    """Crea una máquina generando código automático (MAQ-001) y evitando duplicados."""
    lineas = LineaEnsamblaje.objects.all()
    if request.method == 'POST':
        nombre_maq = request.POST.get('nombre', '').strip()
        codigo = request.POST.get('codigo_inventario', '').strip()

        # Generación automática de código si no se ingresa uno o si viene con el prefijo base 'MAQ-'
        if not codigo or codigo == 'MAQ-':
            ultimo_id = Maquinaria.objects.count() + 1
            codigo = f"MAQ-{ultimo_id:03d}"
            while Maquinaria.objects.filter(codigo_inventario=codigo).exists():
                ultimo_id += 1
                codigo = f"MAQ-{ultimo_id:03d}"

        # Control estricto para evitar códigos duplicados en la base de datos
        if Maquinaria.objects.filter(codigo_inventario=codigo).exists():
            messages.error(request, f'El código de inventario "{codigo}" ya está registrado.')
            return render(request, 'MAQUINARIA/nueva_maquinaria.html', {'lineas': lineas, 'codigo_sugerido': codigo})

        linea = get_object_or_404(LineaEnsamblaje, id=request.POST.get('linea_id'))
        Maquinaria.objects.create(
            nombre=nombre_maq,
            codigo_inventario=codigo,
            linea=linea,
            estado=request.POST.get('estado', 'Operativa'),
            horas_uso=request.POST.get('horas_uso', 0),
            foto=request.FILES.get('foto')
        )
        messages.success(request, f'Maquinaria "{nombre_maq}" registrada correctamente.')
        return redirect('listado_maquinarias')

    # Sugerencia de código automático secuencial (ej. MAQ-001)
    ultimo_id = Maquinaria.objects.count() + 1
    codigo_sugerido = f"MAQ-{ultimo_id:03d}"
    while Maquinaria.objects.filter(codigo_inventario=codigo_sugerido).exists():
        ultimo_id += 1
        codigo_sugerido = f"MAQ-{ultimo_id:03d}"

    return render(request, 'MAQUINARIA/nueva_maquinaria.html', {'lineas': lineas, 'codigo_sugerido': codigo_sugerido})


@login_required(login_url='login')
def editar_maquinaria(request, id):
    """Actualiza la maquinaria verificando que el código no pertenezca a otra máquina."""
    maquinaria = get_object_or_404(Maquinaria, id=id)
    lineas = LineaEnsamblaje.objects.all()
    if request.method == 'POST':
        nombre_maq = request.POST.get('nombre', '').strip()
        codigo = request.POST.get('codigo_inventario', '').strip()

        if Maquinaria.objects.filter(codigo_inventario=codigo).exclude(id=id).exists():
            messages.error(request, f'El código "{codigo}" ya pertenece a otra máquina.')
            return render(request, 'MAQUINARIA/editar_maquinaria.html', {'maquinaria': maquinaria, 'lineas': lineas})

        maquinaria.nombre = nombre_maq
        maquinaria.codigo_inventario = codigo
        maquinaria.linea_id = request.POST.get('linea_id')
        maquinaria.estado = request.POST.get('estado')
        maquinaria.horas_uso = request.POST.get('horas_uso')
        if request.FILES.get('foto'):
            maquinaria.foto = request.FILES.get('foto')
        maquinaria.save()
        messages.success(request, f'Maquinaria "{nombre_maq}" actualizada correctamente.')
        return redirect('listado_maquinarias')

    return render(request, 'MAQUINARIA/editar_maquinaria.html', {'maquinaria': maquinaria, 'lineas': lineas})

@login_required(login_url='login')
def eliminar_maquinaria(request, id):
    """Elimina una maquina del sistema."""
    get_object_or_404(Maquinaria, id=id).delete()
    messages.success(request, 'Maquinaria eliminada.')
    return redirect('listado_maquinarias')


# SUPERVISORES
@login_required(login_url='login')
def listado_supervisores(request):
    """Lista supervisores. Solo deja entrar si eres el Administrador (is_superuser)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acceso denegado: Solo el Administrador puede gestionar los supervisores.')
        return redirect('inicio')
    supervisores = Supervisor.objects.all()
    return render(request, 'SUPERVISORES/listado_supervisor.html', {'supervisores': supervisores})

@login_required(login_url='login')
def nuevo_supervisor(request):
    """Registra un nuevo supervisor desde la consola de administracion."""
    if not request.user.is_superuser:
        messages.error(request, 'Acceso denegado.')
        return redirect('inicio')

    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        correo = request.POST.get('correo')
        contrasena = request.POST.get('contrasena')
        foto = request.FILES.get('foto')

        if Supervisor.objects.filter(cedula=cedula).exists():
            messages.error(request, 'La cédula ingresada ya está registrada.')
            return render(request, 'SUPERVISORES/nuevo_supervisor.html')

        user = User.objects.create_user(username=cedula, email=correo, password=contrasena, first_name=nombre, last_name=apellido)
        Supervisor.objects.create(usuario=user, cedula=cedula, nombre=nombre, apellido=apellido, correo=correo, foto=foto)
        messages.success(request, 'Supervisor registrado correctamente.')
        return redirect('listado_supervisores')

    return render(request, 'SUPERVISORES/nuevo_supervisor.html')

@login_required(login_url='login')
def editar_supervisor(request, id):
    """Actualiza datos del supervisor y sincroniza su usuario de Django."""
    if not request.user.is_superuser:
        messages.error(request, 'Acceso denegado.')
        return redirect('inicio')

    supervisor = get_object_or_404(Supervisor, id=id)
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        if Supervisor.objects.filter(cedula=cedula).exclude(id=id).exists():
            messages.error(request, 'La cédula ingresada ya pertenece a otro supervisor.')
            return render(request, 'SUPERVISORES/editar_supervisor.html', {'supervisor': supervisor})

        supervisor.cedula = cedula
        supervisor.nombre = request.POST.get('nombre')
        supervisor.apellido = request.POST.get('apellido')
        supervisor.correo = request.POST.get('correo')
        if request.FILES.get('foto'):
            supervisor.foto = request.FILES.get('foto')
        supervisor.save()

        if supervisor.usuario:
            supervisor.usuario.first_name = supervisor.nombre
            supervisor.usuario.last_name = supervisor.apellido
            supervisor.usuario.email = supervisor.correo
            supervisor.usuario.save()

        messages.success(request, 'Supervisor actualizado correctamente.')
        return redirect('listado_supervisores')

    return render(request, 'SUPERVISORES/editar_supervisor.html', {'supervisor': supervisor})

@login_required(login_url='login')
def eliminar_supervisor(request, id):
    """Borra al supervisor y su usuario web de acceso."""
    if not request.user.is_superuser:
        messages.error(request, 'Acceso denegado.')
        return redirect('inicio')

    supervisor = get_object_or_404(Supervisor, id=id)
    if supervisor.usuario:
        supervisor.usuario.delete()
    else:
        supervisor.delete()
    messages.success(request, 'Supervisor eliminado.')
    return redirect('listado_supervisores')


# OPERARIOS
@login_required(login_url='login')
def listado_operarios(request):
    """Muestra la lista de operarios de planta."""
    operarios = Operario.objects.all()
    return render(request, 'OPERARIOS/listado_operario.html', {'operarios': operarios})

@login_required(login_url='login')
def nuevo_operario(request):
    """Registra un nuevo operario validando la cedula."""
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        if Operario.objects.filter(cedula=cedula).exists():
            messages.error(request, f'La cédula {cedula} ya pertenece a otro operario.')
            return render(request, 'OPERARIOS/nuevo_operario.html')

        Operario.objects.create(
            cedula=cedula,
            nombres=request.POST.get('nombres'),
            apellidos=request.POST.get('apellidos'),
            telefono=request.POST.get('telefono'),
            correo=request.POST.get('correo'),
            foto=request.FILES.get('foto')
        )
        messages.success(request, 'Operario registrado correctamente.')
        return redirect('listado_operarios')

    return render(request, 'OPERARIOS/nuevo_operario.html')

@login_required(login_url='login')
def editar_operario(request, id):
    """Actualiza la informacion de un operario."""
    operario = get_object_or_404(Operario, id=id)
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        if Operario.objects.filter(cedula=cedula).exclude(id=id).exists():
            messages.error(request, f'La cédula {cedula} ya pertenece a otro operario.')
            return render(request, 'OPERARIOS/editar_operario.html', {'operario': operario})

        operario.cedula = cedula
        operario.nombres = request.POST.get('nombres')
        operario.apellidos = request.POST.get('apellidos')
        operario.telefono = request.POST.get('telefono')
        operario.correo = request.POST.get('correo')
        if request.FILES.get('foto'):
            operario.foto = request.FILES.get('foto')
        operario.save()
        messages.success(request, 'Operario actualizado correctamente.')
        return redirect('listado_operarios')

    return render(request, 'OPERARIOS/editar_operario.html', {'operario': operario})

@login_required(login_url='login')
def eliminar_operario(request, id):
    """Borra un operario."""
    get_object_or_404(Operario, id=id).delete()
    messages.success(request, 'Operario eliminado.')
    return redirect('listado_operarios')


# INSUMOS
@login_required(login_url='login')
def listado_insumos(request):
    """Lista todos los insumos y materias primas."""
    insumos = Insumo.objects.all()
    return render(request, 'INSUMOS/listado_insumo.html', {'insumos': insumos})
@login_required(login_url='login')

@login_required(login_url='login')
def nuevo_insumo(request):
    """Registra una nueva materia prima validando el código y mostrando el nombre en la alerta."""
    if request.method == 'POST':
        nombre_insumo = request.POST.get('nombre', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        
        # Generación automática de código si no ingresaron uno personalizado
        if not codigo or codigo == 'INS-':
            ultimo_id = Insumo.objects.count() + 1
            codigo = f"INS-{ultimo_id:03d}"
            while Insumo.objects.filter(codigo=codigo).exists():
                ultimo_id += 1
                codigo = f"INS-{ultimo_id:03d}"

        if Insumo.objects.filter(codigo=codigo).exists():
            messages.error(request, f'El código de insumo "{codigo}" ya existe.')
            return render(request, 'INSUMOS/nuevo_insumo.html', {'codigo_sugerido': codigo})

        Insumo.objects.create(
            nombre=nombre_insumo,
            codigo=codigo,
            unidad_medida=request.POST.get('unidad_medida'),
            stock_disponible=request.POST.get('stock_disponible', 0),
            foto=request.FILES.get('foto')
        )
        # Aquí se usa el NOMBRE del insumo en lugar del código:
        messages.success(request, f'Insumo "{nombre_insumo}" registrado correctamente.')
        return redirect('listado_insumos')

    # Código sugerido para el campo de formulario
    ultimo_id = Insumo.objects.count() + 1
    codigo_sugerido = f"INS-{ultimo_id:03d}"
    while Insumo.objects.filter(codigo=codigo_sugerido).exists():
        ultimo_id += 1
        codigo_sugerido = f"INS-{ultimo_id:03d}"

    return render(request, 'INSUMOS/nuevo_insumo.html', {'codigo_sugerido': codigo_sugerido})

@login_required(login_url='login')
def editar_insumo(request, id):
    """Edita stock o detalles de la materia prima."""
    insumo = get_object_or_404(Insumo, id=id)
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        if Insumo.objects.filter(codigo=codigo).exclude(id=id).exists():
            messages.error(request, f'El código "{codigo}" ya pertenece a otro insumo.')
            return render(request, 'INSUMOS/editar_insumo.html', {'insumo': insumo})

        insumo.nombre = request.POST.get('nombre')
        insumo.codigo = codigo
        insumo.unidad_medida = request.POST.get('unidad_medida')
        insumo.stock_disponible = request.POST.get('stock_disponible')
        if request.FILES.get('foto'):
            insumo.foto = request.FILES.get('foto')
        insumo.save()
        messages.success(request, 'Insumo actualizado correctamente.')
        return redirect('listado_insumos')

    return render(request, 'INSUMOS/editar_insumo.html', {'insumo': insumo})

@login_required(login_url='login')
def eliminar_insumo(request, id):
    """Borra un insumo."""
    get_object_or_404(Insumo, id=id).delete()
    messages.success(request, 'Insumo eliminado.')
    return redirect('listado_insumos')


# ÓRDENES DE FABRICACIÓN (LOTES)
@login_required(login_url='login')
def listado_ordenes(request):
    """Muestra el listado de lotes. Carga de golpe las tablas unidas para optimizar la velocidad."""
    if request.user.is_superuser:
        ordenes = OrdenFabricacion.objects.select_related('linea', 'maquina', 'supervisor', 'operario_encargado').prefetch_related('detalles_insumos__insumo').all().order_by('prioridad_orden')
    else:
        supervisor = getattr(request.user, 'perfil_supervisor', None)
        ordenes = OrdenFabricacion.objects.select_related('linea', 'maquina', 'supervisor', 'operario_encargado').prefetch_related('detalles_insumos__insumo').filter(supervisor=supervisor).order_by('prioridad_orden') if supervisor else OrdenFabricacion.objects.none()
    
    return render(request, 'ORDEN_FABRICACION/listado_orden.html', {'ordenes': ordenes})


@login_required(login_url='login')
def nueva_orden(request):
    """Crea una orden de fabricación autogenerando el código secuencial (LOT-001) y validando duplicados."""
    lineas = LineaEnsamblaje.objects.all()
    maquinas = Maquinaria.objects.all()
    supervisores = Supervisor.objects.all()
    operarios = Operario.objects.all()
    insumos = Insumo.objects.all()
    supervisor_logueado = getattr(request.user, 'perfil_supervisor', None)

    if request.method == 'POST':
        codigo_lote = request.POST.get('codigo_lote', '').strip()
        producto = request.POST.get('producto', '').strip()

        # GENERACION AUTOMATICA de código secuencial si no ingresan uno personalizado
        if not codigo_lote or codigo_lote == 'LOT-':
            ultimo_id = OrdenFabricacion.objects.count() + 1
            codigo_lote = f"LOT-{ultimo_id:03d}"
            while OrdenFabricacion.objects.filter(codigo_lote=codigo_lote).exists():
                ultimo_id += 1
                codigo_lote = f"LOT-{ultimo_id:03d}"

        # Validación estricta de duplicados
        if OrdenFabricacion.objects.filter(codigo_lote=codigo_lote).exists():
            messages.error(request, f'El código de lote "{codigo_lote}" ya está registrado en el sistema.')
            return render(request, 'ORDEN_FABRICACION/nueva_orden.html', {
                'lineas': lineas, 'maquinas': maquinas, 'supervisores': supervisores, 
                'operarios': operarios, 'insumos': insumos, 'supervisor_logueado': supervisor_logueado,
                'codigo_sugerido': codigo_lote
            })

        linea = get_object_or_404(LineaEnsamblaje, id=request.POST.get('linea_id'))
        
        if not request.user.is_superuser and supervisor_logueado:
            supervisor = supervisor_logueado
        else:
            supervisor = get_object_or_404(Supervisor, id=request.POST.get('supervisor_id'))

        maquina = get_object_or_404(Maquinaria, id=request.POST.get('maquina_id')) if request.POST.get('maquina_id') else None
        operario = get_object_or_404(Operario, id=request.POST.get('operario_id')) if request.POST.get('operario_id') else None

        # 1. Guardar la orden principal
        orden = OrdenFabricacion.objects.create(
            codigo_lote=codigo_lote,
            producto=producto,
            linea=linea,
            maquina=maquina,
            supervisor=supervisor,
            operario_encargado=operario,
            cantidad_programada=request.POST.get('cantidad_programada') or 0,
            cantidad_producida=request.POST.get('cantidad_producida', 0) or 0,
            fecha_inicio_programada=request.POST.get('fecha_inicio_programada'),
            fecha_fin_programada=request.POST.get('fecha_fin_programada'),
            estado=request.POST.get('estado', 'Pendiente')
        )

        # 2. Guardar el detalle de la materia prima usada
        insumo_id = request.POST.get('insumo_id')
        if insumo_id:
            insumo_obj = get_object_or_404(Insumo, id=insumo_id)
            cant_est = request.POST.get('cantidad_estimada') or 0
            cant_uti = request.POST.get('cantidad_utilizada') or 0

            DetalleInsumoLote.objects.create(
                orden=orden,
                insumo=insumo_obj,
                cantidad_estimada=cant_est,
                cantidad_utilizada=cant_uti
            )

        messages.success(request, f'Lote de producción "{codigo_lote}" ({producto}) registrado correctamente.')
        return redirect('listado_ordenes')

    # Sugerencia automática de código secuencial
    ultimo_id = OrdenFabricacion.objects.count() + 1
    codigo_sugerido = f"LOT-{ultimo_id:03d}"
    while OrdenFabricacion.objects.filter(codigo_lote=codigo_sugerido).exists():
        ultimo_id += 1
        codigo_sugerido = f"LOT-{ultimo_id:03d}"

    return render(request, 'ORDEN_FABRICACION/nueva_orden.html', {
        'lineas': lineas, 'maquinas': maquinas, 'supervisores': supervisores, 
        'operarios': operarios, 'insumos': insumos, 'supervisor_logueado': supervisor_logueado,
        'codigo_sugerido': codigo_sugerido
    })


@login_required(login_url='login')
def editar_orden(request, id):
    """Edita la orden de fabricación validando que el código no pertenezca a otro lote."""
    orden = get_object_or_404(OrdenFabricacion, id=id)
    lineas = LineaEnsamblaje.objects.all()
    maquinas = Maquinaria.objects.all()
    supervisores = Supervisor.objects.all()
    operarios = Operario.objects.all()
    insumos = Insumo.objects.all()
    
    detalle_insumo = DetalleInsumoLote.objects.filter(orden=orden).first()

    if request.method == 'POST':
        codigo_lote = request.POST.get('codigo_lote', '').strip()
        producto = request.POST.get('producto', '').strip()

        if OrdenFabricacion.objects.filter(codigo_lote=codigo_lote).exclude(id=id).exists():
            messages.error(request, f'El código de lote "{codigo_lote}" ya pertenece a otra orden registrada.')
            return render(request, 'ORDEN_FABRICACION/editar_orden.html', {
                'orden': orden, 'lineas': lineas, 'maquinas': maquinas, 
                'supervisores': supervisores, 'operarios': operarios, 'insumos': insumos, 
                'detalle_insumo': detalle_insumo
            })

        orden.codigo_lote = codigo_lote
        orden.producto = producto
        orden.linea_id = request.POST.get('linea_id')
        orden.maquina_id = request.POST.get('maquina_id') or None
        
        if request.user.is_superuser:
            orden.supervisor_id = request.POST.get('supervisor_id')
            
        orden.operario_encargado_id = request.POST.get('operario_id') or None
        orden.cantidad_programada = request.POST.get('cantidad_programada') or 0
        orden.cantidad_producida = request.POST.get('cantidad_producida') or 0
        orden.estado = request.POST.get('estado')
        orden.save()

        insumo_id = request.POST.get('insumo_id')
        if insumo_id:
            insumo_obj = get_object_or_404(Insumo, id=insumo_id)
            cant_est = request.POST.get('cantidad_estimada') or 0
            cant_uti = request.POST.get('cantidad_utilizada') or 0

            if detalle_insumo:
                detalle_insumo.insumo = insumo_obj
                detalle_insumo.cantidad_estimada = cant_est
                detalle_insumo.cantidad_utilizada = cant_uti
                detalle_insumo.save()
            else:
                DetalleInsumoLote.objects.create(
                    orden=orden,
                    insumo=insumo_obj,
                    cantidad_estimada=cant_est,
                    cantidad_utilizada=cant_uti
                )

        messages.success(request, f'Lote "{codigo_lote}" actualizado correctamente.')
        return redirect('listado_ordenes')

    return render(request, 'ORDEN_FABRICACION/editar_orden.html', {
        'orden': orden, 'lineas': lineas, 'maquinas': maquinas, 
        'supervisores': supervisores, 'operarios': operarios, 'insumos': insumos, 
        'detalle_insumo': detalle_insumo
    })

@login_required(login_url='login')
def eliminar_orden(request, id):
    """Borra el lote."""
    get_object_or_404(OrdenFabricacion, id=id).delete()
    messages.success(request, 'Lote eliminado.')
    return redirect('listado_ordenes')


# REPORTES DE DESPERDICIOS
@login_required(login_url='login')
def reporte_desperdicios(request):
    """Genera el reporte de desperdicios de materia prima por lote en la planta."""
    if request.user.is_superuser:
        detalles = DetalleInsumoLote.objects.select_related('orden', 'insumo', 'orden__supervisor').all()
    else:
        supervisor = getattr(request.user, 'perfil_supervisor', None)
        detalles = DetalleInsumoLote.objects.select_related('orden', 'insumo', 'orden__supervisor').filter(orden__supervisor=supervisor) if supervisor else DetalleInsumoLote.objects.none()
        
    # Recorremos cada registro ('d') de la lista para calcular la merma dinamicamente antes de mostrar la plantilla
    for d in detalles:
        try:
            # Remplazamos coma por punto por si ingresaron decimales con formato latino
            utilizada = float(str(d.cantidad_utilizada or 0).replace(',', '.'))
        except (ValueError, TypeError):
            utilizada = 0.0

        try:
            estimada = float(str(d.cantidad_estimada or 0).replace(',', '.'))
        except (ValueError, TypeError):
            estimada = 0.0

        try:
            prog = float(str(d.orden.cantidad_programada if d.orden else 0).replace(',', '.'))
        except (ValueError, TypeError):
            prog = 0.0

        try:
            prod = float(str(d.orden.cantidad_producida if d.orden else 0).replace(',', '.'))
        except (ValueError, TypeError):
            prod = 0.0

        # Regla 1: Si se uso mas insumo del estimado originalmente, la diferencia es desperdicio puro
        if utilizada > estimada:
            d.cantidad_desperdicio = utilizada - estimada
        # Regla 2: Si se produjo menos de lo programado, calculamos la merma proporcional a las unidades no entregadas
        elif prog > prod and prog > 0.0 and utilizada > 0.0:
            unidades_defectuosas = prog - prod
            porcentaje_defecto = unidades_defectuosas / prog
            d.cantidad_desperdicio = round(utilizada * porcentaje_defecto, 2)
        else:
            d.cantidad_desperdicio = 0.0

    return render(request, 'reporte_desperdicios.html', {'detalles': detalles})