// Seeded demo orders attached to a product, so the buyer can open a dispute from the product page.
export type DemoOrder = {
  id: string;
  buyer_id: string;
  label: string;
  note: string;
  defaultClaim: string;
};

export const DEMO_ORDERS: Record<string, DemoOrder[]> = {
  prod_size_shoes: [
    {
      id: "order_otp_dispute",
      buyer_id: "buyer_normal",
      label: "Order #OTP-DISPUTE",
      note: "One OTP scanned for 3 items · delivered via a flagged hub",
      defaultClaim: "not_received",
    },
  ],
  prod_fabric_kurti: [
    {
      id: "order_fabric_dispute",
      buyer_id: "buyer_normal",
      label: "Order #FABRIC",
      note: "“Pure cotton” kurti — buyer reports synthetic feel",
      defaultClaim: "item_not_as_described",
    },
    {
      id: "order_serial",
      buyer_id: "buyer_serial_claimer",
      label: "Order #SERIAL",
      note: "Buyer has 7 prior claims — should route to manual review",
      defaultClaim: "item_not_as_described",
    },
  ],
};

export const CLAIM_TYPES = [
  { value: "item_not_as_described", label: "Not as described" },
  { value: "damaged", label: "Arrived damaged" },
  { value: "not_received", label: "Item not received" },
  { value: "wrong_item", label: "Wrong item sent" },
];
