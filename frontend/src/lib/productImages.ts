// product id -> local image paths. Index 0 is the hero image: it leads the product-page
// gallery and is what every thumbnail elsewhere in the app renders (see `productImage`).
export const PRODUCT_IMAGES: Record<string, string[]> = {
  prod_counterfeit_rolex: ["/products/prod_counterfeit_rolex-0.jpg", "/products/prod_counterfeit_rolex-1.jpg", "/products/prod_counterfeit_rolex-2.jpg"],
  prod_viral_honest: ["/products/prod_viral_honest-0.jpg", "/products/prod_viral_honest-1.jpg", "/products/prod_viral_honest-2.jpg", "/products/prod_viral_honest-3.jpg"],
  // Listing photo only. The buyer's dispute photos deliberately live in /evidence/ and are
  // shown in the media comparison — putting them here would make the seller's own listing
  // advertise the sheer fabric the buyer is complaining about.
  prod_fabric_kurti: ["/products/prod_fabric_kurti.png"],
  prod_bag_combo: ["/products/prod_bag_combo.png"],
  prod_size_shoes: ["/products/prod_size_shoes-0.jpg", "/products/prod_size_shoes-1.jpg", "/products/prod_size_shoes-2.jpg", "/products/prod_size_shoes-3.jpg"],
  prod_lowrated_fraud: ["/products/prod_lowrated_fraud-0.jpg"],
  prod_fixable_bedsheet: ["/products/prod_fixable_bedsheet-0.jpg", "/products/prod_fixable_bedsheet-1.jpg", "/products/prod_fixable_bedsheet-2.jpg"],
  prod_damaged_courier: ["/products/prod_damaged_courier-0.jpg"],
  prod_knockoff_loved: ["/products/prod_knockoff_loved-0.jpg", "/products/prod_knockoff_loved-1.jpg", "/products/prod_knockoff_loved-2.jpg"],
  prod_normal_mug: ["/products/prod_normal_mug-0.jpg", "/products/prod_normal_mug-1.jpg"],
  prod_gadget_powerbank: ["/products/prod_gadget_powerbank-0.jpg"],
  prod_gadget_earphones: ["/products/prod_gadget_earphones-0.jpg"],
  prod_beauty_serum: ["/products/prod_beauty_serum-0.jpg", "/products/prod_beauty_serum-1.jpg", "/products/prod_beauty_serum-2.jpg"],
  prod_beauty_lipstick: ["/products/prod_beauty_lipstick-0.jpg"],
  prod_kids_tshirt: ["/products/prod_kids_tshirt-0.jpg", "/products/prod_kids_tshirt-1.jpg", "/products/prod_kids_tshirt-2.jpg", "/products/prod_kids_tshirt-3.jpg"],
  prod_mobile_case: ["/products/prod_mobile_case-0.jpg", "/products/prod_mobile_case-1.jpg", "/products/prod_mobile_case-2.jpg", "/products/prod_mobile_case-3.jpg"],
  prod_jewelry_necklace: ["/products/prod_jewelry_necklace-0.jpg", "/products/prod_jewelry_necklace-1.jpg", "/products/prod_jewelry_necklace-2.jpg"],
  prod_scam_watch: ["/products/prod_scam_watch-0.jpg", "/products/prod_scam_watch-1.jpg", "/products/prod_scam_watch-2.jpg"],
  prod_scam_perfume: ["/products/prod_scam_perfume-0.jpg", "/products/prod_scam_perfume-1.jpg", "/products/prod_scam_perfume-2.jpg"],
};

/** Every image for a product (gallery order). Falls back to the `<id>.jpg` convention. */
export const productImages = (id: string): string[] =>
  PRODUCT_IMAGES[id] ?? [`/products/${id}.jpg`];

/** The single hero image — thumbnails everywhere should use this rather than assuming
 *  a `.jpg` extension, so a product supplying only a `.png` still renders. */
export const productImage = (id: string): string => productImages(id)[0];
