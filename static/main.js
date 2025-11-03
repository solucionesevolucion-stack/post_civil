document.addEventListener("DOMContentLoaded", () => {
  // ---------- Autocomplete invitados ----------
  const inputNombre = document.querySelector('input[name="nombre"]');
  const datalist = document.getElementById("lista-invitados");
  let cacheInvitados = [];

  async function cargarInvitados(q = "") {
    try {
      const url = q ? `/api/invitados?q=${encodeURIComponent(q)}` : `/api/invitados`;
      const res = await fetch(url, { cache: "no-store" });
      const data = await res.json();
      if (data.ok && Array.isArray(data.items)) {
        cacheInvitados = data.items;
        renderDatalist(cacheInvitados);
      }
    } catch (e) {
      console.error("Error cargando invitados:", e);
    }
  }

  function renderDatalist(items) {
    if (!datalist) return;
    datalist.innerHTML = "";
    items.forEach(n => {
      const opt = document.createElement("option");
      opt.value = n;
      datalist.appendChild(opt);
    });
  }

  if (inputNombre && datalist) {
    cargarInvitados();

    let timer = null;
    inputNombre.addEventListener("input", () => {
      clearTimeout(timer);
      const q = inputNombre.value.trim();
      timer = setTimeout(() => cargarInvitados(q), 200);
    });
  }

  // ---------- Menú requerido si asiste ----------
  const si = document.getElementById("asiste-si");
  const no = document.getElementById("asiste-no");
  const menu = document.querySelector('select[name="menu"]');

  function syncMenu() {
    if (!menu) return;
    if (si && si.checked) {
      menu.disabled = false;
      menu.required = true;
    } else {
      menu.required = false;
      menu.disabled = true;
      menu.value = "";
    }
  }
  if (si && no) {
    si.addEventListener("change", syncMenu);
    no.addEventListener("change", syncMenu);
    syncMenu();
  }

  // ---------- Validación extra al enviar ----------
  const form = document.getElementById("form-rsvp");
  if (form && inputNombre) {
    form.addEventListener("submit", (ev) => {
      const nombre = (inputNombre.value || "").trim();
      const coincide = cacheInvitados.some(n => n === nombre);
      if (!coincide) {
        ev.preventDefault();
        if (window.Swal) {
          Swal.fire({
            icon: "error",
            title: "Nombre inválido",
            text: "Elegí tu nombre de la lista de invitados.",
            confirmButtonText: "Entendido"
          });
        } else {
          alert("Elegí tu nombre de la lista de invitados.");
        }
        inputNombre.focus();
        return false;
      }

      if (si && si.checked && menu && !menu.value) {
        ev.preventDefault();
        if (window.Swal) {
          Swal.fire({
            icon: "error",
            title: "Falta el menú",
            text: "Seleccioná Standard o Veggie.",
            confirmButtonText: "Ok"
          });
        } else {
          alert("Seleccioná Standard o Veggie.");
        }
        menu.focus();
        return false;
      }
    });
  }
});
