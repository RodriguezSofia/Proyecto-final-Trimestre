const usuarioLogueado = "{{ 'true' if session.get('usuario_nombre') else 'false' }}" === "true";
let carrito = [];

// Elementos DOM
const carritoCount = document.getElementById("carritoCount");
const carritoCountFloat = document.getElementById("carritoCountFloat");
const listaCarrito = document.getElementById("listaCarrito");

// ─────────── AGREGAR PRODUCTO ───────────
function agregarAlCarrito(idProducto, nombre, precio, numeroBolas) {
    let sabores = [];
    let topping = null;

    for (let i = 1; i <= numeroBolas; i++) {
        const select = document.getElementById(`sabor-${idProducto}-${i}`);
        const idSabor = Number(select.value);
        const nombreSabor = select.options[select.selectedIndex].text;
        sabores.push({ id: idSabor, nombre: nombreSabor });
    }

    const selectTopping = document.getElementById(`topping-${idProducto}`);
    if (selectTopping && selectTopping.value !== "") {
        topping = {
            id: Number(selectTopping.value),
            nombre: selectTopping.options[selectTopping.selectedIndex].text
        };
    }

    carrito.push({
        id_producto: Number(idProducto),
        nombre,
        precio: Number(precio.toString().replace(/\./g, "")),
        sabores,
        topping
    });

    actualizarContadores();
    renderCarrito();
}

// ─────────── ELIMINAR PRODUCTO ───────────
function eliminarProducto(index) {
    carrito.splice(index, 1);
    actualizarContadores();
    renderCarrito();
}

// ─────────── CONTADORES ───────────
function actualizarContadores() {
    if (carritoCount) carritoCount.textContent = carrito.length;
    if (carritoCountFloat) carritoCountFloat.textContent = carrito.length;
}

// ─────────── AGRUPAR CARRITO ───────────
function agruparCarrito(carrito) {
    const agrupado = {};

    carrito.forEach(item => {
        const key = JSON.stringify({
            id: item.id_producto,
            sabores: item.sabores.map(s => s.id),
            topping: item.topping ? item.topping.id : null
        });

        if (!agrupado[key]) {
            agrupado[key] = {
                ...item,
                cantidad: 1
            };
        } else {
            agrupado[key].cantidad += 1;
        }
    });

    return Object.values(agrupado);
}

// ─────────── RENDER CARRITO ───────────
function renderCarrito() {
    if (!listaCarrito) return;

    if (carrito.length === 0) {
        listaCarrito.innerHTML = "<p>Tu carrito está vacío </p>";
        return;
    }

    const carritoAgrupado = agruparCarrito(carrito);

    let total = 0;

    listaCarrito.innerHTML = carritoAgrupado.map((item) => {

        total += item.precio * item.cantidad;

        const precioFormateado = parseInt(item.precio).toLocaleString('es-CO');

        const saboresHTML = item.sabores.map(s => `<br>${s.nombre}`).join("");
        const toppingHTML = item.topping
            ? `<br><small>Topping: ${item.topping.nombre}</small>`
            : "";

        return `
        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
            <div>
                <strong>${item.nombre} x${item.cantidad}</strong> — $${precioFormateado}
                ${saboresHTML}
                ${toppingHTML}
            </div>
        </div>`;
    }).join("");

    const carritoContainer = document.getElementById("carritoContainer");
    carritoContainer.innerHTML = "";

    carritoAgrupado.forEach((item, index) => {
        const div = document.createElement("div");

        div.innerHTML += `<input type="hidden" name="carrito[${index}][id_producto]" value="${item.id_producto}">`;

        item.sabores.forEach((s, i) => {
            div.innerHTML += `<input type="hidden" name="carrito[${index}][sabores][${i}]" value="${s.id}">`;
        });

        if (item.topping) {
            div.innerHTML += `<input type="hidden" name="carrito[${index}][topping]" value="${item.topping.id}">`;
        }

        div.innerHTML += `<input type="hidden" name="carrito[${index}][precio]" value="${item.precio}">`;

        carritoContainer.appendChild(div);
    });

    const totalDiv = document.createElement("div");
    totalDiv.classList.add("mt-3", "fw-bold", "text-end");
    totalDiv.innerHTML = `Total: $${total.toLocaleString('es-CO')}`;

    carritoContainer.appendChild(totalDiv);
}
// ─────────── COMPRA ───────────
function validarCompra() {
    if (!usuarioLogueado) {
        const loginModal = new bootstrap.Modal(document.getElementById("modalLogin"));
        loginModal.show();
        return;
    }
    comprar();
}

function comprar() {
    if (carrito.length === 0) {
        alert("Tu carrito está vacío");
        return;
    }

    localStorage.setItem("carrito", JSON.stringify(carrito));

    const total = carrito.reduce((suma, p) => suma + p.precio, 0);
    localStorage.setItem("total", total);

    localStorage.setItem("usuario", "{{ session.get('usuario_nombre') }}");

    window.location.href = "/confirmar_pedido";
}

// ─────────── CARGA INICIAL ───────────
document.addEventListener("DOMContentLoaded", () => {
    const carritoGuardado = JSON.parse(localStorage.getItem("carrito"));
    if (carritoGuardado && carritoGuardado.length > 0) {
        carrito = carritoGuardado;
        actualizarContadores();
        renderCarrito();
    }
});