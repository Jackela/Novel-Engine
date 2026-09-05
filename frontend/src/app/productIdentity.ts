export interface ProductIdentity {
  readonly name: string;
  readonly version: string;
}

/** Build-time projection of the server package manifest product authority. */
export const productIdentity: ProductIdentity = Object.freeze({
  name: __PRODUCT_IDENTITY__.name,
  version: __PRODUCT_IDENTITY__.version,
});

export const productLabel = `${productIdentity.name} ${productIdentity.version}`;
