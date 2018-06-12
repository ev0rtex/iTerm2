#import "iTermBackgroundColorRenderer.h"

#import "iTermPIUArray.h"
#import "iTermTextRenderer.h"

@interface iTermBackgroundColorRendererTransientState()
@end

@implementation iTermBackgroundColorRendererTransientState {
    iTerm2::PIUArray<iTermBackgroundColorPIU> _pius;
}

- (NSUInteger)sizeOfNewPIUBuffer {
    return sizeof(iTermBackgroundColorPIU) * self.cellConfiguration.gridSize.width * self.cellConfiguration.gridSize.height;
}

- (void)setColorRLEs:(const iTermMetalBackgroundColorRLE *)rles
               count:(size_t)count
                 row:(int)row
       repeatingRows:(int)repeatingRows {
    vector_float2 cellSize = simd_make_float2(self.cellConfiguration.cellSize.width, self.cellConfiguration.cellSize.height);
    const int height = self.cellConfiguration.gridSize.height;
    for (int i = 0; i < count; i++) {
        iTermBackgroundColorPIU &piu = *_pius.get_next();
        piu.color = rles[i].color;
        piu.runLength = rles[i].count;
        piu.numRows = repeatingRows;
        piu.offset = simd_make_float2(cellSize.x * (float)rles[i].origin,
                                      cellSize.y * (height - row - repeatingRows));
    }
}

- (void)enumerateSegments:(void (^)(const iTermBackgroundColorPIU *, size_t))block {
    const int n = _pius.get_number_of_segments();
    for (int segment = 0; segment < n; segment++) {
        const iTermBackgroundColorPIU *array = _pius.start_of_segment(segment);
        size_t size = _pius.size_of_segment(segment);
        block(array, size);
    }
}

@end

@interface iTermBackgroundColorRenderer() <iTermMetalDebugInfoFormatter>
@end

@implementation iTermBackgroundColorRenderer {
    iTermMetalCellRenderer *_cellRenderer;
    iTermMetalMixedSizeBufferPool *_piuPool;
}

- (instancetype)initWithDevice:(id<MTLDevice>)device {
    self = [super init];
    if (self) {
        _cellRenderer = [[iTermMetalCellRenderer alloc] initWithDevice:device
                                                    vertexFunctionName:@"iTermBackgroundColorVertexShader"
                                                  fragmentFunctionName:@"iTermBackgroundColorFragmentShader"
                                                              blending:[[iTermMetalBlending alloc] init]
                                                        piuElementSize:sizeof(iTermBackgroundColorPIU)
                                                   transientStateClass:[iTermBackgroundColorRendererTransientState class]];
        _cellRenderer.formatterDelegate = self;
        // TODO: The capacity here is a total guess. But this would be a lot of rows to have.
        _piuPool = [[iTermMetalMixedSizeBufferPool alloc] initWithDevice:device
                                                                capacity:512
                                                                    name:@"background color PIU"];
    }
    return self;
}

- (iTermMetalFrameDataStat)createTransientStateStat {
    return iTermMetalFrameDataStatPqCreateBackgroundColorTS;
}

- (BOOL)rendererDisabled {
    return NO;
}

- (__kindof iTermMetalRendererTransientState * _Nonnull)createTransientStateForCellConfiguration:(iTermCellRenderConfiguration *)configuration
                                   commandBuffer:(id<MTLCommandBuffer>)commandBuffer {
    __kindof iTermMetalCellRendererTransientState * _Nonnull transientState =
        [_cellRenderer createTransientStateForCellConfiguration:configuration
                                              commandBuffer:commandBuffer];
    [self initializeTransientState:transientState];
    return transientState;
}

- (void)initializeTransientState:(iTermBackgroundColorRendererTransientState *)tState {
    tState.vertexBuffer = [_cellRenderer newQuadOfSize:tState.cellConfiguration.cellSize
                                           poolContext:tState.poolContext];
    tState.vertexBuffer.label = @"Vertices";
}


- (void)drawWithFrameData:(iTermMetalFrameData *)frameData
           transientState:(nonnull __kindof iTermMetalRendererTransientState *)transientState {
    iTermBackgroundColorRendererTransientState *tState = transientState;
    [tState enumerateSegments:^(const iTermBackgroundColorPIU *pius, size_t numberOfInstances) {
        id<MTLBuffer> piuBuffer = [self->_piuPool requestBufferFromContext:tState.poolContext
                                                                      size:numberOfInstances * sizeof(*pius)
                                                                     bytes:pius];
        piuBuffer.label = @"PIUs";
        [self->_cellRenderer drawWithTransientState:tState
                                      renderEncoder:frameData.renderEncoder
                                   numberOfVertices:6
                                       numberOfPIUs:numberOfInstances
                                      vertexBuffers:@{ @(iTermVertexInputIndexVertices): tState.vertexBuffer,
                                                       @(iTermVertexInputIndexPerInstanceUniforms): piuBuffer,
                                                       @(iTermVertexInputIndexOffset): tState.offsetBuffer }
                                    fragmentBuffers:@{}
                                           textures:@{} ];
    }];
}

#pragma mark - iTermMetalDebugInfoFormatter

- (void)writeVertexBuffer:(id<MTLBuffer>)buffer index:(NSUInteger)index toFolder:(NSURL *)folder {
    if (index == iTermVertexInputIndexPerInstanceUniforms) {
        iTermBackgroundColorPIU *pius = (iTermBackgroundColorPIU *)buffer.contents;
        NSMutableString *s = [NSMutableString string];
        for (int i = 0; i < buffer.length / sizeof(*pius); i++) {
            [s appendFormat:@"offset=(%@, %@) runLength=%@ numRows=%@ color=(%@, %@, %@, %@)\n",
             @(pius[i].offset.x),
             @(pius[i].offset.y),
             @(pius[i].runLength),
             @(pius[i].numRows),
             @(pius[i].color.x),
             @(pius[i].color.y),
             @(pius[i].color.z),
             @(pius[i].color.w)];
        }
        NSURL *url = [folder URLByAppendingPathComponent:@"vertexBuffer.iTermVertexInputIndexPerInstanceUniforms.txt"];
        [s writeToURL:url atomically:NO encoding:NSUTF8StringEncoding error:nil];
    }
}

@end