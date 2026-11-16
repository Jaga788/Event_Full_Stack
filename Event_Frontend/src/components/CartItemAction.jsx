import { useState } from "react";
import { useCart } from "../context/CartContext";

function CartItemAction({ product, buttonClassName, onRequireCustomer }) {
  const { cart, addToCart, increaseQty, decreaseQty } = useCart();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const cartItem = cart.find((item) => item.catalogKey === product.id);

  const runAction = async (action) => {
    setError("");
    setBusy(true);
    try {
      await action();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const addItem = async () => {
    setError("");
    if (!onRequireCustomer()) return;
    await runAction(() => addToCart(product));
  };

  return (
    <>
      {cartItem ? (
        <div className="cart-quantity-control" aria-label={`${product.name} quantity`}>
          <button
            type="button"
            className="quantity-change"
            aria-label={`Decrease ${product.name} quantity`}
            disabled={busy}
            onClick={() => runAction(() => decreaseQty(cartItem.id))}
          >
            −
          </button>
          <span aria-live="polite">{cartItem.quantity}</span>
          <button
            type="button"
            className="quantity-change"
            aria-label={`Increase ${product.name} quantity`}
            disabled={busy || product.unit === "per event"}
            onClick={() => runAction(() => increaseQty(cartItem.id))}
          >
            +
          </button>
        </div>
      ) : (
        <button type="button" className={buttonClassName} onClick={addItem} disabled={busy}>
          Add to Cart
        </button>
      )}
      {error && <p className="error card-error" role="alert">{error}</p>}
    </>
  );
}

export default CartItemAction;
