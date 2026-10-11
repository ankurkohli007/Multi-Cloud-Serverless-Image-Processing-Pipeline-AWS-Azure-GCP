module.exports = async function (context, req, inputDocuments) {
    context.res = {
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: inputDocuments
    };
};