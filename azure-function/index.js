module.exports = async function (context, myBlob) {
    context.log(`New file uploaded via Event Grid: ${context.bindingData.name}, Size: ${myBlob.length} bytes`);
};