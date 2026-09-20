"""Schema transformer and validator for Myntra product data.
Normalizes raw Myntra product payload into user's exact required JSON schema.
"""

import re
import html
from typing import Dict, Any, Optional, List


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean HTML tags and whitespace."""
    if not text:
        return None
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', text)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split()).strip()


def clean_image_url(url: Optional[str], width: int = 540, height: int = 720, quality: int = 90) -> Optional[str]:
    """Resolve Myntra dynamic image URL parameters."""
    if not url:
        return None
    # Replace template variables
    cleaned = url.replace('($height)', str(height))
    cleaned = cleaned.replace('($width)', str(width))
    cleaned = cleaned.replace('($qualityPercentage)', str(quality))
    cleaned = cleaned.replace('$height', str(height))
    cleaned = cleaned.replace('$width', str(width))
    cleaned = cleaned.replace('$qualityPercentage', str(quality))
    if cleaned.startswith('http://'):
        cleaned = 'https://' + cleaned[7:]
    return cleaned


def _to_float(value: Any, default: float = 0.0) -> float:
    """Coerce price-like values into floats without crashing on formatted strings."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^0-9.]+", "", value)
        if cleaned:
            try:
                return float(cleaned)
            except ValueError:
                return default
    return default


def _to_int(value: Any, default: int = 0) -> int:
    """Coerce loosely formatted numeric values into ints."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+", value.replace(",", ""))
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                return default
    return default


def parse_pdp_to_schema(pdp_data: Dict[str, Any], raw_url: str = "") -> Dict[str, Any]:
    """
    Transforms Myntra PDP dictionary into the exact required JSON specification.
    """
    pdp = pdp_data or {}
    
    # -------------------------------------------------------------
    # 1. Product Info
    # -------------------------------------------------------------
    product_id = pdp.get("id") or pdp.get("productId")
    style_group = pdp.get("styleGroup") or pdp.get("styleId") or product_id
    sku = f"M{product_id}" if product_id else str(style_group or "")
    
    brand_info = pdp.get("brand")
    if isinstance(brand_info, dict):
        brand_name = brand_info.get("name") or brand_info.get("value") or ""
    else:
        brand_name = str(brand_info or "")

    title = pdp.get("name") or pdp.get("title") or pdp.get("productName") or ""
    
    analytics = pdp.get("analytics") or {}
    article_type = pdp.get("articleType") or {}
    
    raw_cat = (
        analytics.get("category")
        or (article_type.get("typeName") if isinstance(article_type, dict) else None)
        or "Clothing"
    )
    if isinstance(raw_cat, dict):
        category = raw_cat.get("typeName") or raw_cat.get("name") or "Clothing"
    else:
        category = str(raw_cat or "Clothing")

    raw_subcat = (
        analytics.get("subCategory")
        or analytics.get("articleType")
        or "Topwear"
    )
    if isinstance(raw_subcat, dict):
        sub_category = raw_subcat.get("typeName") or raw_subcat.get("name") or "Topwear"
    else:
        sub_category = str(raw_subcat or "Topwear")

    raw_gender = analytics.get("gender") or pdp.get("gender") or "Unisex"
    if isinstance(raw_gender, dict):
        gender = raw_gender.get("typeName") or raw_gender.get("name") or "Unisex"
    else:
        gender = str(raw_gender or "Unisex")
    
    # Clean product url
    landing_url = pdp.get("landingPageUrl") or ""
    if raw_url:
        product_url = raw_url
    elif landing_url:
        product_url = f"https://www.myntra.com/{landing_url.lstrip('/')}"
    elif product_id:
        product_url = f"https://www.myntra.com/product/{product_id}"
    else:
        product_url = ""

    from brands import get_brand_classification
    sys_attrs = pdp.get("systemAttributes") or []
    is_myntra, b_type = get_brand_classification(brand_name, sys_attrs)

    product_info = {
        "product_id": int(product_id) if product_id and str(product_id).isdigit() else product_id,
        "sku": sku,
        "brand": brand_name,
        "is_myntra_label": is_myntra,
        "brand_type": b_type,
        "title": title,
        "category": category,
        "sub_category": sub_category,
        "gender": gender,
        "product_url": product_url
    }

    # -------------------------------------------------------------
    # 2. Pricing
    # -------------------------------------------------------------
    price_data = pdp.get("price") or {}
    mrp = _to_float(price_data.get("mrp") or pdp.get("mrp"))
    selling_price = _to_float(
        price_data.get("discounted")
        or price_data.get("selling")
        or pdp.get("discountedPrice")
        or pdp.get("sellingPrice")
        or mrp
    )

    # Keep price ordering sane when the payload is partial or malformed.
    if mrp <= 0 and selling_price > 0:
        mrp = selling_price
    if selling_price <= 0 and mrp > 0:
        selling_price = mrp
    if mrp > 0 and selling_price > mrp:
        mrp = selling_price

    discount_pct = 0
    if mrp > 0 and mrp > selling_price:
        discount_pct = round(((mrp - selling_price) / mrp) * 100)
    elif pdp.get("discount"):
        discount_pct = max(0, min(100, _to_int(pdp.get("discount"), 0)))

    # Extract available offers
    offers_list: List[str] = []
    raw_offers = pdp.get("offers", []) or []
    raw_app_offers = pdp.get("applicableOffers", []) or []
    coupon_data = pdp.get("couponData", []) or []

    for item in raw_offers + raw_app_offers:
        if isinstance(item, dict):
            offer_text = item.get("title") or item.get("description") or item.get("code")
            if offer_text and offer_text not in offers_list:
                offers_list.append(clean_text(offer_text) or offer_text)

    for c in coupon_data:
        if isinstance(c, dict):
            c_desc = c.get("couponDescription") or c.get("couponCode")
            if c_desc and c_desc not in offers_list:
                offers_list.append(c_desc)

    pricing = {
        "mrp": mrp,
        "selling_price": selling_price,
        "discount_percentage": discount_pct,
        "currency": "INR",
        "taxes_included": True,
        "available_offers": offers_list
    }

    # -------------------------------------------------------------
    # 3. Media
    # -------------------------------------------------------------
    albums = pdp.get("media", {}).get("albums", []) or []
    image_gallery: List[str] = []
    
    if albums:
        first_album = albums[0]
        for img in first_album.get("images", []):
            raw_src = img.get("secureSrc") or img.get("src") or img.get("imageURL")
            if raw_src:
                clean_img = clean_image_url(raw_src)
                if clean_img and clean_img not in image_gallery:
                    image_gallery.append(clean_img)
    
    # Fallback if no album images
    if not image_gallery:
        for extra_img in pdp.get("images", []) or []:
            if isinstance(extra_img, dict):
                src = extra_img.get("src") or extra_img.get("secureSrc")
            else:
                src = str(extra_img)
            c_img = clean_image_url(src)
            if c_img and c_img not in image_gallery:
                image_gallery.append(c_img)

    primary_image = image_gallery[0] if image_gallery else None
    gallery = image_gallery[1:] if len(image_gallery) > 1 else (image_gallery if image_gallery else [])

    # Video URL
    video_url = None
    videos = pdp.get("media", {}).get("videos", []) or []
    if videos and isinstance(videos[0], dict):
        v = videos[0]
        raw_v_url = v.get("url") or v.get("videoUrl") or v.get("id")
        if raw_v_url:
            if raw_v_url.startswith("http"):
                video_url = raw_v_url
            else:
                video_url = f"https://assets.myntassets.com/video/upload/v1/assets/videos/{raw_v_url}"

    media = {
        "primary_image": primary_image,
        "image_gallery": gallery,
        "video_url": video_url
    }

    # -------------------------------------------------------------
    # 4. Inventory and Sizes
    # -------------------------------------------------------------
    raw_sizes = pdp.get("sizes") or []
    sizes_available = []
    is_in_stock = False

    for sz in raw_sizes:
        if not isinstance(sz, dict):
            continue
        label = sz.get("label") or sz.get("size") or sz.get("name") or "Standard"
        sku_id = sz.get("skuId") or sz.get("id")
        available = bool(sz.get("available", False))
        if available:
            is_in_stock = True

        # Calculate exact inventory count across sellers
        seller_data = sz.get("sizeSellerData", []) or []
        inv_count = 0
        if available:
            if seller_data:
                inv_count = sum(
                    (s.get("availableCount") or s.get("sellableInventoryCount") or 0)
                    for s in seller_data
                    if isinstance(s, dict)
                )
            else:
                inv_count = _to_int(sz.get("inventory"), 1)
        else:
            inv_count = 0

        sizes_available.append({
            "size": str(label),
            "sku_id": int(sku_id) if sku_id and str(sku_id).isdigit() else sku_id,
            "available": available,
            "inventory_count": max(0, _to_int(inv_count))
        })

    # Fit & Model Sizing
    attrs = pdp.get("articleAttributes") or {}
    fit = (
        attrs.get("Fit")
        or attrs.get("Brand Fit Name")
        or "Regular Fit"
    )

    model_sizing = None
    for p_detail in pdp.get("productDetails", []) or []:
        if isinstance(p_detail, dict) and "SIZE" in p_detail.get("title", "").upper():
            raw_desc = p_detail.get("description")
            model_sizing = clean_text(raw_desc) or raw_desc
            break

    inventory_and_sizes = {
        "is_in_stock": is_in_stock,
        "sizes_available": sizes_available,
        "fit": fit,
        "model_sizing": model_sizing
    }

    # -------------------------------------------------------------
    # 5. Specifications
    # -------------------------------------------------------------
    specifications = {
        "fabric": attrs.get("Fabrics") or attrs.get("Fabric") or "Cotton",
        "weave_type": attrs.get("Weave Type") or attrs.get("Weave") or "Woven",
        "pattern": attrs.get("Patterns") or attrs.get("Pattern") or "Solid",
        "sleeve_length": attrs.get("Sleeve Length") or "Regular",
        "collar": attrs.get("Collar") or "Regular Collar",
        "length": attrs.get("Length") or "Regular",
        "hemline": attrs.get("Hemline") or "Straight",
        "wash_care": attrs.get("Wash Care") or attrs.get("Care") or "Machine Wash"
    }

    # Add all remaining article attributes
    for k, v in attrs.items():
        k_clean = k.lower().replace(" ", "_").replace("-", "_")
        if k_clean not in specifications and isinstance(v, (str, int, float)):
            specifications[k_clean] = v

    # -------------------------------------------------------------
    # 6. Delivery and Policies
    # -------------------------------------------------------------
    flags = pdp.get("flags") or {}
    serv = pdp.get("serviceability") or {}
    
    return_days = serv.get("returnPeriod")
    if not return_days or return_days == 0:
        return_days = 14 if flags.get("isReturnable", True) else 0

    delivery_and_policies = {
        "pincode_serviceable": True,
        "estimated_delivery_days": 4,
        "cod_available": bool(flags.get("codEnabled", True)),
        "return_window_days": int(return_days),
        "exchange_available": bool(flags.get("isExchangeable", True))
    }

    # -------------------------------------------------------------
    # 7. Ratings and Reviews
    # -------------------------------------------------------------
    ratings_obj = pdp.get("ratings") or {}
    try:
        avg_rating = round(float(ratings_obj.get("averageRating") or 0.0), 1)
    except (ValueError, TypeError):
        avg_rating = 0.0

    try:
        total_ratings = int(ratings_obj.get("totalCount") or 0)
    except (ValueError, TypeError):
        total_ratings = 0

    rev_info = ratings_obj.get("reviewInfo") or {}
    try:
        total_reviews = int(rev_info.get("reviewsCount") or 0)
    except (ValueError, TypeError):
        total_reviews = 0

    breakdown = {
        "5_star": 0,
        "4_star": 0,
        "3_star": 0,
        "2_star": 0,
        "1_star": 0
    }
    for r_item in ratings_obj.get("ratingInfo", []) or []:
        star_num = r_item.get("rating")
        count = r_item.get("count", 0)
        key = f"{star_num}_star"
        if key in breakdown:
            try:
                breakdown[key] = int(count)
            except (ValueError, TypeError):
                breakdown[key] = 0

    ratings_and_reviews = {
        "average_rating": avg_rating,
        "total_ratings_count": total_ratings,
        "total_reviews_count": total_reviews,
        "rating_breakdown": breakdown
    }

    # Final combined schema
    return {
        "product_info": product_info,
        "pricing": pricing,
        "media": media,
        "inventory_and_sizes": inventory_and_sizes,
        "specifications": specifications,
        "delivery_and_policies": delivery_and_policies,
        "ratings_and_reviews": ratings_and_reviews
    }
