// The claim categories a buyer can file. `value` is the backend claim_type; `wrong_colour`
// is colour-sensitive (the vision fingerprint compares colour only for these claims).
export const CLAIM_TYPES = [
  { value: "item_not_as_described", label: "Not as described" },
  { value: "fabric_mismatch", label: "Wrong material" },
  { value: "damaged", label: "Arrived damaged" },
  { value: "not_received", label: "Item not received" },
  { value: "wrong_colour", label: "Wrong colour sent" },
];
