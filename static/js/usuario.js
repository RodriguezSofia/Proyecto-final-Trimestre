        const usuarioLogueado = "{{ 'true' if session.get('usuario_nombre') else 'false' }}" === "true"
        function toggleMenu() {
            const menu = document.getElementById("dropdownPerfil");
            if (menu) {
                menu.classList.toggle("oculto");
                console.log("Menú clickeado, clase oculto cambiada");
            } else {
                console.log("Error: No encontré el ID 'dropdownPerfil'");
            }
        }
        function guardarDatosPerfil() {
            const nombre = document.getElementById("nuevoNombre").value;
            const correo = document.getElementById("nuevoCorreo").value;

            fetch('/actualizar_perfil', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombre: nombre, correo: correo })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Actualiza los textos en la ventanita sin recargar
                    document.getElementById("nombreTexto").textContent = nombre;
                    document.getElementById("correoTexto").textContent = correo;
                    
                    Swal.fire({
                        title: "¡Guardado!",
                        text: "Datos actualizados correctamente",
                        icon: "success",
                        confirmButtonColor: "#ff9ecf"
                    });
                    toggleEditar(); // Cierra el formulario de edición
                }
            });
        }

        function toggleEditar() {
            document.getElementById("formEditar").classList.toggle("oculto");
        }
    
        inputFoto.addEventListener("change", function () {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    const base64Image = e.target.result;
                    
                    // Enviamos la imagen al servidor
                    fetch('/actualizar_foto', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ foto_url: base64Image })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if(data.success) {
                            foto.src = base64Image; // Cambia la foto en la ventanita
                            // Cambia también la foto de la burbuja pequeña en la nav
                            document.querySelector(".avatar-nav").src = base64Image; 
                        }
                    });
                };
                reader.readAsDataURL(file);
            }
        });
    
        // Cerrar si hacen clic fuera
        window.addEventListener('click', function(e) {
            const menu = document.getElementById("dropdownPerfil");
            const wrapper = document.querySelector('.perfil-dropdown-wrapper');
            
            if (menu && !wrapper.contains(e.target)) {
                menu.classList.add('oculto');
            }
        });