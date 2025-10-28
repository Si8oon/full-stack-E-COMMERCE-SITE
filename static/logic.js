// ===== Menu =====
const menuBtn = document.querySelector('.menu-btn');
const navUl = document.querySelector('.navbar ul');

if (menuBtn) {
  menuBtn.addEventListener('click', () => {
    navUl.classList.toggle('active');
    menuBtn.classList.toggle('active');
  });
}

// ===== Cart Logic =====
const addBtn = document.querySelectorAll(".addBtn");
const cartList = document.getElementById("cartList");
const totalDisplay = document.getElementById("totalDisplay");
const clearCart = document.getElementById("clearCart");

let cart = JSON.parse(localStorage.getItem("cart")) || [];
let total = parseFloat(localStorage.getItem("cartTotal")) || 0;

function renderCart() {
  if (!cartList) return;
  cartList.innerHTML = "";

  if (cart.length === 0) {
    cartList.innerHTML = "<p>Your cart is empty 😢</p>";
    totalDisplay.textContent = "Total: ₵0.00";
    return;
  }

  total = 0;
  cart.forEach((item, index) => {
    const li = document.createElement("li");
    li.textContent = `${item.name} - ₵${item.price.toFixed(2)}`;

    const removeBtn = document.createElement("button");
    removeBtn.textContent = "Remove";
    removeBtn.classList.add("removeBtn");

    removeBtn.addEventListener("click", () => {
      cart.splice(index, 1);
      localStorage.setItem("cart", JSON.stringify(cart));
      renderCart();
    });

    li.appendChild(removeBtn);
    cartList.appendChild(li);
    total += item.price;
  });

  totalDisplay.textContent = `Total: ₵${total.toFixed(2)}`;
  localStorage.setItem("cartTotal", total.toFixed(2));
}

if (addBtn.length > 0) {
  addBtn.forEach(btn => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".card");
      const name = card.dataset.name;
      const price = parseFloat(card.dataset.price);

      const existingItem = cart.find(item => item.name === name);
      if (existingItem) {
        alert(`${name} is already in your cart!`);
        return;
      }

      cart.push({ name, price });
      total += price;

      localStorage.setItem("cart", JSON.stringify(cart));
      localStorage.setItem("cartTotal", total.toFixed(2));
      renderCart();
    });
  });
}

if (clearCart) {
  clearCart.addEventListener("click", () => {
    localStorage.removeItem("cart");
    localStorage.removeItem("cartTotal");
    cart = [];
    renderCart();
  });
}

renderCart();
