async function generateCaption(tagNames) {
    const base = process.env.AZ_OPENAI_ENDPOINT.trim().replace(/\/$/, "");
    const key = process.env.AZ_OPENAI_KEY.trim();
    const url = `${base}/openai/v1/responses`;
    const body = JSON.stringify({
        model: process.env.AZ_OPENAI_DEPLOYMENT.trim(),
        input: `You write alt-text for an image catalog. You cannot see the image. Use ONLY these detected tags: ${tagNames.join(", ")}. Reply with JSON only: {"caption": "<one sentence>", "hashtags": ["#a","#b","#c"]}`
    });
    let res = await fetch(url, { method: "POST", headers: { "api-key": key, "Content-Type": "application/json" }, body });
    if (res.status === 401) {
        res = await fetch(url, { method: "POST", headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" }, body });
    }
    const data = await res.json();
    const msg = (data.output || []).find(o => o.type === "message");
    const text = msg?.content?.find(c => c.type === "output_text")?.text;
    return text ?? JSON.stringify({ httpStatus: res.status, ...data });
}

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
            headers: { "Ocp-Apim-Subscription-Key": process.env.VISION_KEY, "Content-Type": "application/json" },
            body: JSON.stringify({ url: imageUrl })
        }
    );
    const result = await response.json();
    let aiCaption = null;
    try {
        const tagNames = (result.tags || []).slice(0, 10).map(t => t.name);
        if (tagNames.length) aiCaption = await generateCaption(tagNames);
    } catch (e) {
        aiCaption = "GenAI step failed: " + e.message;
    }
    context.res = {
        status: response.status,
        headers: { "Content-Type": "application/json" },
        body: {
            caption: result.description?.captions?.[0]?.text,
            tags: result.tags?.slice(0, 10),
            isFlagged: result.adult?.isAdultContent || result.adult?.isRacyContent,
            aiCaption,
            raw: result
        }
    };
};