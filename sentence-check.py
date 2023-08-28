#!/usr/pkg/bin/python3.11
"""

              LICENSE FOR THE PYTHON BINDINGS TO LINK GRAMMAR
              -----------------------------------------------

Copyright (c) 2012, MetaMetrics
Copyright (c) 2014, Linas Vepstas
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies, 
either expressed or implied, of MetaMetrics.
"""

import sys
import re
import argparse

from linkgrammar import (Sentence, ParseOptions, Dictionary,
                         LG_Error, LG_TimerExhausted, Clinkgrammar as clg)

def nsuffix(q):
    return '' if q == 1 else 's'

class Formatter(argparse.HelpFormatter):
    """ Display the "lang" argument as a first one, as in link-parser. """
    def _format_usage(self, usage, actions, groups, prefix):
        usage_message = super(Formatter, self)._format_usage(usage, actions, groups, prefix)
        return re.sub(r'(usage: \S+) (.*) \[lang]', r'\1 [lang] \2', str(usage_message))

#-----------------------------------------------------------------------------#

is_stdin_atty = sys.stdin.isatty()

PROMPT = "sentence-check: " if is_stdin_atty else ""
DISPLAY_GUESSES = True   # Display regex and POS guesses
BATCH_LABELS = '*: '

args = argparse.ArgumentParser(formatter_class=Formatter)
args.add_argument('lang', nargs='?', default='en',
                  help="language or dictionary location")
args.add_argument("-v", "--verbosity", type=int,default=0,
                  choices=range(0,199), metavar='[0-199]',
                  help= "1: Basic verbosity; 2-4: Trace; >5: Debug")
args.add_argument("-p", "--position", action="store_true", default=True,
                  help="show word sentence position")
args.add_argument("-nm", "--no-morphology", dest='morphology', action='store_false',
                  help="do not display morphology")
args.add_argument("-i", "--interactive", action="store_true",
                  help="interactive mode after each result")
args.add_argument('-f', '--file', nargs='?',
                  help="input file name")

arg = args.parse_args()

try:
    lgdict = Dictionary(arg.lang)
except LG_Error:
    # The default error handler will print the error message
    args.print_usage()
    sys.exit(2)

po = ParseOptions(verbosity=arg.verbosity)

po.max_null_count = 999  # > allowed maximum number of words
po.linkage_limit = 10000 # maximum number of linkages to generate
po.max_parse_time = 10   # actual parse timeout may be about twice bigger
po.spell_guess = True if DISPLAY_GUESSES else False
po.display_morphology = arg.morphology

line_no = 0

try:
    f = open(arg.file)
    sentence_text = f.readline()
except:
    exit(0)

while sentence_text:
    line_no = line_no + 1

    if sentence_text.strip() == '':
        sentence_text = f.readline()
        continue

    sent = Sentence(str(sentence_text), lgdict, po)
    try:
        linkages = sent.parse()
    except LG_TimerExhausted:
        print('Sentence too complex for parsing in ~{} second{}.'.format(
            po.max_parse_time,nsuffix(po.max_parse_time)))
    if not linkages:
        print('Error occurred - sentence ignored.', sentence_text)
    if len(linkages) <= 0:
        print('Cannot parse the input sentence', sentence_text)
    null_count = sent.null_count()

    linkages = list(linkages)

    correction_found = False
    # search for correction suggestions
    for l in linkages:
        for word in l.words():
            if word.find(r'.#') > 0:
                correction_found = True
                break
        if correction_found:
            break

    if correction_found:
        print(" - with correction", end='')

    # Show results with unlinked words or guesses
    if arg.position or guess_found or correction_found or null_count != 0:
        result_no = 0
        uniqe_parse = {}
        for linkage in linkages:
            words = list(linkage.words())
            if str(words) in uniqe_parse or result_no > 0:
                continue
            result_no += 1
            uniqe_parse[str(words)] = True

            if arg.position:
                words_char = []
                words_byte = []
                unlinked_char_nths = []
                for wi, w in enumerate(words):
                    words_char.append(w + str((linkage.word_char_start(wi), linkage.word_char_end(wi))))
                    words_byte.append(w + str((linkage.word_byte_start(wi), linkage.word_byte_end(wi))))
                    if w[0] == '[' and w[-1] == ']':
                        unlinked_char_nths.append(linkage.word_char_start(wi))

                for n in unlinked_char_nths:
                    print(u"{}:LINE:{}:COLUMN:{}: grammartical-error".format(arg.file, line_no, n + 1))

    if arg.interactive:
        print("Interactive session (^D to end):")
        import code
        code.interact(local=locals())

    sentence_text = f.readline()
