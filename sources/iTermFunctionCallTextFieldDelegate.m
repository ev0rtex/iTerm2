//
//  iTermFunctionCallTextFieldDelegate.m
//  iTerm2SharedARC
//
//  Created by George Nachman on 5/19/18.
//

#import "iTermFunctionCallTextFieldDelegate.h"

#import "iTermAPIHelper.h"
#import "iTermFunctionCallSuggester.h"
#import "iTermVariables.h"
#import "NSArray+iTerm.h"
#import "NSObject+iTerm.h"

@interface iTermFunctionCallTextFieldDelegate()<
    NSControlTextEditingDelegate>

@property (nonatomic) BOOL isAutocompleting;
@property (nonatomic, strong) NSString *lastEntry;
@property (nonatomic) BOOL backspaceKey;

@end

@implementation iTermFunctionCallTextFieldDelegate {
    iTermFunctionCallSuggester *_suggester;
    __weak id _passthrough;
}

- (instancetype)initWithPaths:(NSArray<NSString *> *)paths
                  passthrough:(id)passthrough {
    self = [super init];
    if (self) {
        NSDictionary<NSString *,NSArray<NSString *> *> *signatures =
            [[iTermAPIHelper sharedInstance] registeredFunctionSignatureDictionary];
        _suggester = [[iTermFunctionCallSuggester alloc] initWithFunctionSignatures:signatures
                                                                              paths:paths
                                                                 matchFunctionsOnly:YES];
        _passthrough = passthrough;
    }
    return self;
}

- (void)controlTextDidChange:(NSNotification *)obj {
    NSTextView *fieldEditor =  obj.userInfo[@"NSFieldEditor"];

    if (self.isAutocompleting == NO  && !self.backspaceKey) {
        self.isAutocompleting = YES;
        self.lastEntry = [[fieldEditor string] copy];
        [fieldEditor complete:nil];
        self.isAutocompleting = NO;
    }

    self.backspaceKey = NO;
}

- (NSArray *)control:(NSControl *)control
            textView:(NSTextView *)textView
         completions:(NSArray *)words
 forPartialWordRange:(NSRange)charRange
 indexOfSelectedItem:(NSInteger *)index {
    if (!self.lastEntry) {
        return nil;
    }
    if (NSMaxRange(charRange) != self.lastEntry.length) {
        // Can't deal with suggestions in the middle!
        return nil;
    }
    NSArray<NSString *> *suggestions = [_suggester suggestionsForString:self.lastEntry];

    if (!suggestions.count) {
        return nil;
    }

    return [suggestions mapWithBlock:^id(NSString *s) {
        return [s substringFromIndex:charRange.location];
    }];

}

- (BOOL)control:(NSControl *)control
       textView:(NSTextView *)textView
doCommandBySelector:(SEL)commandSelector{
    if (commandSelector == @selector(deleteBackward:)) {
        self.backspaceKey = YES;
    }

    return NO;
}

- (void)focusReportingTextFieldWillBecomeFirstResponder:(iTermFocusReportingTextField *)sender {
    NSTextView *fieldEditor = [NSTextView castFrom:[[sender window] fieldEditor:YES forObject:sender]];
    if (self.isAutocompleting == NO  && !self.backspaceKey) {
        self.isAutocompleting = YES;
        self.lastEntry = [[fieldEditor string] copy];
        [fieldEditor complete:nil];
        self.isAutocompleting = NO;
    }

    self.backspaceKey = NO;
    if ([_passthrough respondsToSelector:_cmd]) {
        [_passthrough focusReportingTextFieldWillBecomeFirstResponder:sender];
    }
}

- (void)controlTextDidBeginEditing:(NSNotification *)obj {
    if ([_passthrough respondsToSelector:_cmd]) {
        [_passthrough controlTextDidBeginEditing:obj];
    }
}

- (void)controlTextDidEndEditing:(NSNotification *)obj {
    if ([_passthrough respondsToSelector:_cmd]) {
        [_passthrough controlTextDidEndEditing:obj];
    }
}

@end

