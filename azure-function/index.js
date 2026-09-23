module.exports = async function (context, myBlob) {
    const fileName = context.bindingData.name;
    const fileSize = myBlob.length;

    context.log(`New file uploaded: ${fileName}, Size: ${fileSize} bytes`);

    context.bindings.outputDocument = {
        id: fileName,
        imageId: fileName,
        size: fileSize,
        uploadTimestamp: new Date().toISOString()
    };
};