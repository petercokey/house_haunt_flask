import cloudinary
import cloudinary.uploader

def upload_house_image(file, public_id_prefix):
    """
    Uploads image to Cloudinary and returns secure URL
    """
    result = cloudinary.uploader.upload(
        file,
        folder="house_images",
        public_id=public_id_prefix,
        overwrite=True,
        resource_type="image",
    )

    return result["secure_url"]

