"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getAnimatedImageDurationInSeconds = void 0;
const create_image_decoder_1 = require("./create-image-decoder");
const getAnimatedImageDurationInSeconds = async ({ resolvedSrc, signal, requestInit, contentType, }) => {
    const { decoder, selectedTrack } = await (0, create_image_decoder_1.createImageDecoder)({
        resolvedSrc,
        signal,
        requestInit,
        contentType,
    });
    try {
        const { image } = await decoder.decode({
            frameIndex: selectedTrack.frameCount - 1,
            completeFramesOnly: true,
        });
        try {
            if (image.duration === null) {
                throw new Error('Could not determine animated image duration');
            }
            return (image.timestamp + image.duration) / 1000000;
        }
        finally {
            image.close();
        }
    }
    finally {
        decoder.close();
    }
};
exports.getAnimatedImageDurationInSeconds = getAnimatedImageDurationInSeconds;
