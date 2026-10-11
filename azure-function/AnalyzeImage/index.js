module.exports = async function (context, req) {
    const imageUrl = req.query.url;
    if (!imageUrl) {
        context.res = { status: 400, body: { error: "Provide ?url=<public or SAS image URL>" } };
        return;
    }
    const endpoint = process.env.VISION_ENDPOINT.replace(/\/$/, "");
    const response = await fetch(
        `${endpoint}/vision/v3.2/analyze?visualFeatures=Tags,Description,Adult`,
        {
            method: "POST",
            headers: {
                "Ocp-Apim-Subscription-Key": process.env.VISION_KEY,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url: imageUrl })
        }
    );
    const result = await response.json();
    context.res = {
        status: response.status,
        headers: { "Content-Type": "application/json" },
        body: {
            caption: result.description?.captions?.[0]?.text,
            tags: result.tags?.slice(0, 10),
            isFlagged: result.adult?.isAdultContent || result.adult?.isRacyContent,
            raw: result
        }
    };
};